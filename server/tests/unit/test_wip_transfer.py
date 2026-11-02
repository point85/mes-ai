"""
Tests for transferring completed WIP units/lots into inventory.
"""

from __future__ import annotations

import importlib
import pkgutil
import uuid
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import mes.core
import mes.framework.auth.models  # noqa: F401
from mes.core.inventory.models import InventoryBalance, InventoryTransaction, StorageLocation
from mes.core.material.models import MaterialDefinition
from mes.core.operations.models import OperationsRequest
from mes.core.product_def.models import (
    SegmentMaterialRequirement,
    OperationsDefinition,
    OperationsDefinitionMaterialAssignment,
    ProcessSegment,    ProductDefinition,
)
from mes.core.uom.models import UnitOfMeasure
from mes.core.wip.exceptions import (
    AlreadyTransferredException,
    InvalidWIPTransitionException,
    NoOutputMaterialException,
    NoTransferLocationException,
)
from mes.core.wip.models import Lot, SegmentResponseLot, SegmentResponseUnit, Unit
from mes.core.wip.transfer import get_transfer_info, transfer_to_inventory
from mes.framework.db import BaseModel

for _pkg in pkgutil.iter_modules(mes.core.__path__):
    try:
        importlib.import_module(f"mes.core.{_pkg.name}.models")
    except ModuleNotFoundError:
        pass


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
    await engine.dispose()


async def _setup(
    session: AsyncSession, symbol: str, *, finished: bool = True, product_type: str = "discrete",
):
    uom = UnitOfMeasure(
        symbol=symbol, name=symbol, uom_type="base", uom_class="test", multiplier=1.0, offset=0.0,
    )
    session.add(uom)
    await session.flush()
    product = ProductDefinition(
        name="P", code=f"P-{uuid.uuid4().hex[:6]}", uom_id=uom.id, product_type=product_type,
    )
    route = OperationsDefinition(name="R")
    session.add_all([product, route])
    await session.flush()
    order = OperationsRequest(
        order_number=f"O-{uuid.uuid4().hex[:6]}", product_id=product.id,
        route_id=route.id, quantity_ordered=10,
    )
    material = MaterialDefinition(
        name="FG", code=f"FG-{uuid.uuid4().hex[:6]}", material_type="finished",
        uom_id=uom.id, uom_rel=uom,
    )
    location = StorageLocation(name="FG", code="FG", location_type="storage")
    session.add_all([order, material, location])
    await session.flush()
    if finished:
        session.add(OperationsDefinitionMaterialAssignment(route_id=route.id, material_id=material.id))
        await session.flush()
    return product, order, material, location


async def _complete_step(session, kind, wip, order, location_id):
    """Record a completed step (with the given transfer location) in the WIP history."""
    step = ProcessSegment(
        route_id=order.route_id, sequence=1, name="Last", transfer_location_id=location_id,
    )
    session.add(step)
    await session.flush()
    now = datetime.now(timezone.utc)
    common = dict(
        step_id=step.id, entered_at=now, exited_at=now,
        entered_at_utc=now.replace(tzinfo=None), exited_at_utc=now.replace(tzinfo=None),
        result="pass",
    )
    if kind == "unit":
        session.add(SegmentResponseUnit(unit_id=wip.id, **common))
    else:
        session.add(SegmentResponseLot(lot_id=wip.id, quantity_in=wip.quantity, **common))
    await session.flush()


@pytest.mark.asyncio
async def test_unit_is_received_once_into_step_location(session):
    product, order, material, location = await _setup(session, "EA")
    unit = Unit(serial_number="SN-100", order_id=order.id, product_id=product.id, status="completed")
    session.add(unit)
    await session.flush()
    await _complete_step(session, "unit", unit, order, location.id)

    info = await get_transfer_info(session, "unit", unit.id)
    assert info["available"] and info["location_code"] == "FG"

    lot, qty, loc_id = await transfer_to_inventory(session, "unit", unit.id)
    assert loc_id == location.id
    assert lot.lot_number == "SN-100"
    assert lot.material_id == material.id
    assert lot.tracking_method == "unit"
    assert qty == 1.0

    balances = (await session.execute(select(InventoryBalance))).scalars().all()
    assert [(b.location_id, b.quantity_on_hand) for b in balances] == [(location.id, 1.0)]
    txn = (await session.execute(select(InventoryTransaction))).scalar_one()
    assert (
        txn.transaction_type,
        txn.to_location_id,
        txn.quantity,
        txn.reference_type,
        txn.reference_id,
    ) == ("receive", location.id, 1.0, "wip_unit", unit.id)

    assert (await get_transfer_info(session, "unit", unit.id))["transferred"] is True
    # Already counted when it completed its route, so not counted again.
    assert order.quantity_completed == 0
    with pytest.raises(AlreadyTransferredException):
        await transfer_to_inventory(session, "unit", unit.id)


@pytest.mark.asyncio
async def test_mid_route_queued_lot_transfers_good_quantity(session):
    product, order, material, location = await _setup(session, "kg", product_type="process")
    lot = Lot(lot_number="LN-7", order_id=order.id, product_id=product.id, quantity=7, status="queued")
    session.add(lot)
    await session.flush()
    await _complete_step(session, "lot", lot, order, location.id)

    material_lot, qty, _ = await transfer_to_inventory(session, "lot", lot.id)
    assert lot.status == "finished"
    assert order.quantity_completed == 7
    assert qty == 7.0
    assert material_lot.tracking_method == "lot"
    assert material_lot.quantity_on_hand == 7.0


@pytest.mark.asyncio
async def test_process_product_with_each_uom_is_lot_tracked(session):
    product, order, _material, location = await _setup(session, "EA", product_type="process")
    lot = Lot(lot_number="LN-8", order_id=order.id, product_id=product.id, quantity=5, status="queued")
    session.add(lot)
    await session.flush()
    await _complete_step(session, "lot", lot, order, location.id)

    material_lot, qty, _ = await transfer_to_inventory(session, "lot", lot.id)
    assert material_lot.tracking_method == "lot"
    assert material_lot.quantity_on_hand == qty == 5.0


@pytest.mark.asyncio
async def test_discrete_product_with_non_each_uom_is_unit_tracked(session):
    product, order, _material, location = await _setup(session, "kg", product_type="discrete")
    unit = Unit(serial_number="SN-200", order_id=order.id, product_id=product.id, status="completed")
    session.add(unit)
    await session.flush()
    await _complete_step(session, "unit", unit, order, location.id)

    material_lot, qty, _ = await transfer_to_inventory(session, "unit", unit.id)
    assert material_lot.tracking_method == "unit"
    assert qty == material_lot.quantity_on_hand == 1.0


@pytest.mark.asyncio
async def test_step_without_transfer_location_is_an_error(session):
    product, order, _material, _location = await _setup(session, "EA")
    unit = Unit(serial_number="SN-101", order_id=order.id, product_id=product.id, status="completed")
    session.add(unit)
    await session.flush()
    await _complete_step(session, "unit", unit, order, None)
    assert (await get_transfer_info(session, "unit", unit.id))["available"] is False
    with pytest.raises(NoTransferLocationException):
        await transfer_to_inventory(session, "unit", unit.id)


@pytest.mark.asyncio
async def test_in_process_wip_cannot_transfer(session):
    product, order, _material, location = await _setup(session, "EA")
    unit = Unit(serial_number="SN-103", order_id=order.id, product_id=product.id, status="in_process")
    session.add(unit)
    await session.flush()
    await _complete_step(session, "unit", unit, order, location.id)
    with pytest.raises(InvalidWIPTransitionException):
        await transfer_to_inventory(session, "unit", unit.id)


@pytest.mark.asyncio
async def test_route_without_output_material_is_an_error(session):
    product, order, _material, location = await _setup(session, "EA", finished=False)
    unit = Unit(serial_number="SN-102", order_id=order.id, product_id=product.id, status="completed")
    session.add(unit)
    await session.flush()
    await _complete_step(session, "unit", unit, order, location.id)
    with pytest.raises(NoOutputMaterialException):
        await transfer_to_inventory(session, "unit", unit.id)

@pytest.mark.asyncio
async def test_output_material_found_by_produced_requirement(session):
    product, order, material, location = await _setup(session, "EA", finished=False)
    unit = Unit(serial_number="SN-103", order_id=order.id, product_id=product.id, status="completed")
    session.add(unit)
    await session.flush()
    await _complete_step(session, "unit", unit, order, location.id)
    step = (await session.execute(select(ProcessSegment))).scalar_one()
    session.add(SegmentMaterialRequirement(
        step_id=step.id, material_id=material.id, quantity=1, uom_id=material.uom_id,
        material_use="produced",
    ))
    await session.flush()
    lot, _, _ = await transfer_to_inventory(session, "unit", unit.id)
    assert lot.material_id == material.id


@pytest.mark.asyncio
async def test_output_material_found_by_product_code(session):
    product, order, material, location = await _setup(session, "EA", finished=False)
    material.code = product.code
    unit = Unit(serial_number="SN-104", order_id=order.id, product_id=product.id, status="completed")
    session.add(unit)
    await session.flush()
    await _complete_step(session, "unit", unit, order, location.id)
    lot, _, _ = await transfer_to_inventory(session, "unit", unit.id)
    assert lot.material_id == material.id
