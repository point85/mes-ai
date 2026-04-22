"""
Demo: Order processors for the CPG and Electronics demos.

These are concrete implementations of ``OrderProcessor`` that show how
to convert inbound ERP orders into MES ``OperationsRequest`` entities
plus WIP (Lots for CPG, Units for Electronics).

End users should study these examples and create their own processor
tailored to their business rules.

Customisation points
────────────────────
• **Order-number generation** — currently uses the ERP reference.
  You might prefix it with a plant code or timestamp.
• **Auto-release** — both demos release the order immediately.
  A real factory might require a supervisor approval step.
• **Lot / Unit creation** — CPG creates one lot per order (quantity =
  order quantity).  Electronics creates one unit per piece.  Your
  factory might split lots by shift, machine, or container size.
• **Route selection** — currently looks up the product's default route.
  Override this if your ERP specifies a routing explicitly.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.adapters.erp.inbound_queue import OrderProcessor, ProcessorResult
from mes.core.product_def.models import (
    OperationsDefinition,
    OperationsDefinitionProductAssignment,
    ProductDefinition,
)
from mes.core.operations.models import OperationsRequest
from mes.core.operations.service import OperationsRequestService
from mes.core.wip.service import LotService, UnitService

logger = logging.getLogger("mes.demo.order_processors")


# ── Helpers ───────────────────────────────────────────────────────────────

def _parse_dt(value: Any) -> datetime | None:
    """Parse a datetime value from a payload (string or datetime)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


async def _resolve_product(
    session: AsyncSession, product_code: str,
) -> ProductDefinition:
    """Look up a product by code. Raises if not found."""
    result = await session.execute(
        select(ProductDefinition).where(
            ProductDefinition.code == product_code,
            ProductDefinition.is_active.is_(True),
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise ValueError(f"Product '{product_code}' not found in MES")
    return product


async def _resolve_route(
    session: AsyncSession, product_id: UUID,
) -> OperationsDefinition | None:
    """Return the first active route for a product, or None."""
    result = await session.execute(
        select(OperationsDefinition)
        .join(
            OperationsDefinitionProductAssignment,
            OperationsDefinitionProductAssignment.route_id == OperationsDefinition.id,
        )
        .where(
            OperationsDefinitionProductAssignment.product_id == product_id,
            OperationsDefinitionProductAssignment.is_active.is_(True),
            OperationsDefinition.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def _find_existing_order(
    session: AsyncSession, erp_reference: str,
) -> OperationsRequest | None:
    """Check if a production order with this ERP reference already exists."""
    result = await session.execute(
        select(OperationsRequest).where(
            OperationsRequest.erp_reference == erp_reference,
            OperationsRequest.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


# ── CPG Lot Processor ────────────────────────────────────────────────────

class CPGLotProcessor(OrderProcessor):
    """
    Converts inbound ERP orders into ProductionOrders with **one Lot**
    per order (batch/process manufacturing).

    Flow for each order:
      1. Resolve product by code.
      2. Look up the default process route.
      3. Create a OperationsRequest (status = ``created``).
      4. Release the order (``created`` → ``released``).
      5. Create a single Lot with ``quantity = order.quantity_ordered``.

    The lot number is derived from the ERP reference:
      ``LOT-{erp_reference}``
    """

    @property
    def name(self) -> str:
        return "cpg-lot-processor"

    async def process_order(
        self,
        session: AsyncSession,
        payload: dict[str, Any],
    ) -> ProcessorResult:
        erp_ref = payload["erp_reference"]
        product_code = payload["product_code"]
        qty = payload["quantity_ordered"]

        # 1. Idempotency — skip if order already exists for this ERP ref
        existing = await _find_existing_order(session, erp_ref)
        if existing is not None:
            logger.info(
                "Order for ERP ref %s already exists (id=%s), skipping",
                erp_ref, existing.id,
            )
            return ProcessorResult(order_id=str(existing.id))

        # 2. Resolve product
        product = await _resolve_product(session, product_code)

        # 3. Resolve route
        route = await _resolve_route(session, product.id)

        # 4. Create production order
        order = await OperationsRequestService.create_order(
            session,
            order_number=erp_ref,
            product_id=product.id,
            route_id=route.id if route else None,
            quantity_ordered=qty,
            priority=payload.get("priority", 0),
            erp_reference=erp_ref,
            planned_start=_parse_dt(payload.get("planned_start")),
            planned_end=_parse_dt(payload.get("planned_end")),
        )

        # 5. Release the order
        await OperationsRequestService.release_order(session, order.id)

        # 6. Create one lot for the full quantity
        lot_number = f"LOT-{erp_ref}"
        lot = await LotService.create_lot(
            session,
            order_id=order.id,
            lot_number=lot_number,
            product_id=product.id,
            quantity=qty,
        )

        logger.info(
            "CPG processor: ERP %s → order %s, lot %s (qty=%d)",
            erp_ref, order.order_number, lot.lot_number, qty,
        )
        return ProcessorResult(
            order_id=str(order.id),
            wip_ids=[str(lot.id)],
        )


# ── Electronics Unit Processor ───────────────────────────────────────────

class ElectronicsUnitProcessor(OrderProcessor):
    """
    Converts inbound ERP orders into ProductionOrders with **one Unit
    per piece** (discrete/serial-number manufacturing).

    Flow for each order:
      1. Resolve product by code.
      2. Look up the default process route.
      3. Create a OperationsRequest (status = ``created``).
      4. Release the order (``created`` → ``released``).
      5. Create N Units (one per ordered quantity) with serial numbers
         ``SN-{erp_reference}-00001`` … ``SN-{erp_reference}-NNNNN``.
    """

    @property
    def name(self) -> str:
        return "electronics-unit-processor"

    async def process_order(
        self,
        session: AsyncSession,
        payload: dict[str, Any],
    ) -> ProcessorResult:
        erp_ref = payload["erp_reference"]
        product_code = payload["product_code"]
        qty = payload["quantity_ordered"]

        # 1. Idempotency — skip if order already exists for this ERP ref
        existing = await _find_existing_order(session, erp_ref)
        if existing is not None:
            logger.info(
                "Order for ERP ref %s already exists (id=%s), skipping",
                erp_ref, existing.id,
            )
            return ProcessorResult(order_id=str(existing.id))

        # 2. Resolve product
        product = await _resolve_product(session, product_code)

        # 3. Resolve route
        route = await _resolve_route(session, product.id)

        # 4. Create production order
        order = await OperationsRequestService.create_order(
            session,
            order_number=erp_ref,
            product_id=product.id,
            route_id=route.id if route else None,
            quantity_ordered=qty,
            priority=payload.get("priority", 0),
            erp_reference=erp_ref,
            planned_start=_parse_dt(payload.get("planned_start")),
            planned_end=_parse_dt(payload.get("planned_end")),
        )

        # 5. Release the order
        await OperationsRequestService.release_order(session, order.id)

        # 6. Create one unit per piece
        unit_ids: list[str] = []
        for seq in range(1, qty + 1):
            serial = f"SN-{erp_ref}-{seq:05d}"
            unit = await UnitService.create_unit(
                session,
                order_id=order.id,
                serial_number=serial,
                product_id=product.id,
            )
            unit_ids.append(str(unit.id))

        logger.info(
            "Electronics processor: ERP %s → order %s, %d units",
            erp_ref, order.order_number, qty,
        )
        return ProcessorResult(
            order_id=str(order.id),
            wip_ids=unit_ids,
        )
