"""
WIP-TRACK: Transfer completed WIP (units and lots) into inventory.

A completed unit or lot becomes an inventory item of the route's output
material and is received into a storage location (e.g. Finished Goods).
The WIP serial / lot number becomes the inventory lot number, so the
inventory record can always be traced back to the WIP record.
"""

from __future__ import annotations

import logging
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.core.inventory.models import StorageLocation
from mes.core.inventory.service import InventoryTransactionService
from mes.core.material.models import MaterialDefinition, MaterialLot
from mes.core.material.service import MaterialLotService
from mes.core.operations.service import OperationsRequestService
from mes.core.product_def.models import (
    OperationsDefinitionMaterialAssignment,
    ProcessSegment,
    ProductDefinition,
    SegmentMaterialRequirement,
)
from mes.core.routing.service import RoutingEngineService

from .exceptions import (
    AlreadyTransferredException,
    InvalidWIPTransitionException,
    NoOutputMaterialException,
    NoTransferLocationException,
)
from .models import Lot, SegmentResponseLot, SegmentResponseUnit, Unit
from .service import LotService, UnitService

logger = logging.getLogger("mes.wip")

OUTPUT_MATERIAL_TYPE = "finished"


async def resolve_output_material(
    session: AsyncSession, wip: Unit | Lot, identifier: str,
) -> MaterialDefinition:
    """
    Determine the material produced by a WIP unit/lot.

    Uses the material recorded on the WIP when present; otherwise the single
    finished material assigned to the order's route, produced by one of its
    steps, or sharing the order product's code. Anything else is an error.
    """
    if wip.material_id is not None:
        material = await session.get(MaterialDefinition, wip.material_id)
        if material is not None:
            return material

    route = await RoutingEngineService.get_route_for_order(session, wip.order_id)
    rows = (await session.execute(
        select(MaterialDefinition)
        .join(
            OperationsDefinitionMaterialAssignment,
            OperationsDefinitionMaterialAssignment.material_id == MaterialDefinition.id,
        )
        .where(
            OperationsDefinitionMaterialAssignment.route_id == route.id,
            OperationsDefinitionMaterialAssignment.is_active.is_(True),
            MaterialDefinition.is_active.is_(True),
            MaterialDefinition.material_type == OUTPUT_MATERIAL_TYPE,
        )
    )).scalars().all()
    if len(rows) == 1:
        return rows[0]

    # A finished material the route produces at one of its steps.
    produced = (await session.execute(
        select(MaterialDefinition)
        .join(
            SegmentMaterialRequirement,
            SegmentMaterialRequirement.material_id == MaterialDefinition.id,
        )
        .join(ProcessSegment, ProcessSegment.id == SegmentMaterialRequirement.step_id)
        .where(
            ProcessSegment.route_id == route.id,
            SegmentMaterialRequirement.material_use == "produced",
            MaterialDefinition.is_active.is_(True),
            MaterialDefinition.material_type == OUTPUT_MATERIAL_TYPE,
        )
        .distinct()
    )).scalars().all()
    if len(produced) == 1:
        return produced[0]

    # A finished material sharing the order product's code.
    product = await session.get(ProductDefinition, wip.product_id)
    if product is not None:
        same_code = (await session.execute(
            select(MaterialDefinition).where(
                MaterialDefinition.code == product.code,
                MaterialDefinition.is_active.is_(True),
                MaterialDefinition.material_type == OUTPUT_MATERIAL_TYPE,
            )
        )).scalars().all()
        if len(same_code) == 1:
            return same_code[0]

    raise NoOutputMaterialException(identifier, route.name, len(rows))


async def _tracking_for_product(session: AsyncSession, product_id: UUID) -> str | None:
    """Discrete products are unit tracked and process products lot tracked; others use the material default."""
    product = await session.get(ProductDefinition, product_id)
    return {"discrete": "unit", "process": "lot"}.get(product.product_type) if product else None


async def _wip_identity(
    session: AsyncSession, kind: str, wip_id: UUID,
) -> tuple[Unit | Lot, str, float]:
    if kind == "unit":
        wip: Unit | Lot = await UnitService.get_unit(session, wip_id)
        return wip, wip.serial_number, 1.0
    wip = await LotService.get_lot(session, wip_id)
    # Lot quantity is reduced by step scrap, so it is the good quantity.
    return wip, wip.lot_number, float(wip.quantity)


async def _last_completed_step(
    session: AsyncSession, kind: str, wip_id: UUID,
) -> ProcessSegment | None:
    history = SegmentResponseUnit if kind == "unit" else SegmentResponseLot
    fk = history.unit_id if kind == "unit" else history.lot_id
    step_id = (await session.execute(
        select(history.step_id)
        .where(fk == wip_id, history.exited_at.is_not(None))
        .order_by(history.exited_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    return await session.get(ProcessSegment, step_id) if step_id else None


async def get_transfer_info(
    session: AsyncSession, kind: Literal["unit", "lot"], wip_id: UUID,
) -> dict:
    """
    Describe whether a WIP unit/lot can be transferred to inventory now.

    A transfer is offered when the step the item last completed defines a
    transfer location, the item is not currently being processed, and it is
    not already in inventory.
    """
    wip, identifier, _ = await _wip_identity(session, kind, wip_id)
    info: dict = {
        "available": False, "location_id": None,
        "location_code": None, "location_name": None, "transferred": False,
    }
    if wip.status == "finished":
        info["transferred"] = True
        return info
    if wip.status not in ("queued", "completed"):
        return info
    step = await _last_completed_step(session, kind, wip_id)
    if step is None or step.transfer_location_id is None:
        return info
    location = await session.get(StorageLocation, step.transfer_location_id)
    if location is None:
        return info
    existing = await session.execute(
        select(MaterialLot.id).where(MaterialLot.lot_number == identifier),
    )
    info["transferred"] = existing.first() is not None
    info["available"] = not info["transferred"]
    info.update(
        location_id=str(location.id),
        location_code=location.code,
        location_name=location.name,
    )
    return info


async def transfer_to_inventory(
    session: AsyncSession,
    kind: Literal["unit", "lot"],
    wip_id: UUID,
    reason: str | None = None,
) -> tuple[MaterialLot, float, UUID]:
    """
    Create the inventory item for a WIP unit/lot and receive it into the
    transfer location of the step it last completed. Returns the material
    lot, the received quantity and the location id.
    """
    wip, identifier, quantity = await _wip_identity(session, kind, wip_id)

    if wip.status == "finished":
        raise AlreadyTransferredException(identifier)

    if wip.status not in ("queued", "completed"):
        raise InvalidWIPTransitionException(
            identifier, wip.status, "transfer to inventory",
        )

    step = await _last_completed_step(session, kind, wip_id)
    if step is None or step.transfer_location_id is None:
        raise NoTransferLocationException(identifier)
    location_id = step.transfer_location_id

    existing = await session.execute(
        select(MaterialLot.id).where(MaterialLot.lot_number == identifier),
    )
    if existing.first() is not None:
        raise AlreadyTransferredException(identifier)

    material = await resolve_output_material(session, wip, identifier)

    tracking = await _tracking_for_product(session, wip.product_id)
    if (tracking or material.tracking_method) == "unit" and quantity != 1:
        raise InvalidWIPTransitionException(
            identifier, f"quantity {quantity:g}",
            f"transfer as a unit-tracked item of material '{material.code}'",
        )

    material_lot = await MaterialLotService.create_lot(
        session,
        material_id=material.id,
        lot_number=identifier,
        quantity_on_hand=0.0,
        tracking_override=tracking,
    )
    await InventoryTransactionService.receive(
        session,
        material_lot_id=material_lot.id,
        to_location_id=location_id,
        quantity=quantity,
        reason=reason or f"Transferred from WIP {kind} {identifier}",
        reference_id=wip.id,
        reference_type=f"wip_{kind}",
    )
    material_lot.status = "finished"
    # The WIP leaves the route: it is now an inventory item. Items that
    # already finished their route were counted as completed; a mid-route
    # transfer counts toward the order's completed quantity here.
    if wip.status != "completed":
        await OperationsRequestService.increment_completed(
            session, wip.order_id, int(quantity),
        )
    wip.status = "finished"
    await session.flush()
    logger.info(
        "Transferred WIP %s %s to inventory (material=%s, qty=%s, location=%s)",
        kind, identifier, material.code, quantity, location_id,
    )
    return material_lot, quantity, location_id
