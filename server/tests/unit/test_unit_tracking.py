"""
Behavioural tests for unit-tracked (serial number) inventory.

Materials whose tracking attribute is "unit" are unit tracked: quantity is always one,
there is a single storage location, and the inventory cannot be adjusted.
Materials tracked as "lot" keep the existing behaviour regardless of UOM.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import importlib
import pkgutil

import mes.core
import mes.framework.auth.models  # noqa: F401
from mes.core.inventory.exceptions import InvalidTransactionException
from mes.core.inventory.models import InventoryBalance, StorageLocation
from mes.core.inventory.service import InventoryTransactionService
from mes.core.material.exceptions import UnitTrackedRestrictionException
from mes.core.material.models import MaterialDefinition
from mes.core.material.schemas import MaterialLotRead
from mes.core.material.service import MaterialLotService
from mes.core.uom.models import UnitOfMeasure
from mes.framework.db import BaseModel

for _pkg in pkgutil.iter_modules(mes.core.__path__):
    try:
        importlib.import_module(f"mes.core.{_pkg.name}.models")
    except ModuleNotFoundError:
        pass

_TABLES = [
    BaseModel.metadata.tables[name]
    for name in (
        "units_of_measure", "sites", "material_definitions", "material_lots",
        "storage_locations", "inventory_balances", "inventory_transactions",
    )
]


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
    await engine.dispose()


async def _uom(session: AsyncSession, symbol: str) -> UnitOfMeasure:
    uom = UnitOfMeasure(
        symbol=symbol, name=symbol, uom_type="base", uom_class="test", multiplier=1.0, offset=0.0,
    )
    session.add(uom)
    await session.flush()
    return uom


async def _material(session: AsyncSession, symbol: str, tracking: str = "lot") -> MaterialDefinition:
    uom = await _uom(session, symbol)
    material = MaterialDefinition(
        name=symbol, code=f"M-{symbol}-{uuid.uuid4().hex[:6]}", material_type="raw", uom_id=uom.id,
        uom_rel=uom, tracking=tracking,
    )
    session.add(material)
    await session.flush()
    return material


async def _location(session: AsyncSession, code: str) -> StorageLocation:
    location = StorageLocation(name=code, code=code, location_type="storage")
    session.add(location)
    await session.flush()
    return location


@pytest.mark.asyncio
async def test_tracking_method_follows_tracking_attribute(session):
    each = await _material(session, "EA", "unit")
    kilos = await _material(session, "kg", "lot")
    each_as_lot = await _material(session, "PC", "lot")
    assert each.tracking_method == "unit"
    assert kilos.tracking_method == "lot"
    assert each_as_lot.tracking_method == "lot"

    # Fresh identity map: serializing a new lot must not need a lazy load.
    each_id = each.id
    await session.commit()
    session.expunge_all()
    unit_lot = await MaterialLotService.create_lot(
        session, material_id=each_id, lot_number="SN-1", quantity_on_hand=500.0,
    )
    assert MaterialLotRead.model_validate(unit_lot).tracking_method == "unit"
    assert unit_lot.quantity_on_hand == 1.0


@pytest.mark.asyncio
async def test_unit_receive_and_transfer_keep_single_location(session):
    material = await _material(session, "EA", "unit")
    lot = await MaterialLotService.create_lot(session, material_id=material.id, lot_number="SN-2")
    recv, rack = await _location(session, "RECV"), await _location(session, "RACK")

    await InventoryTransactionService.receive(
        session, material_lot_id=lot.id, to_location_id=recv.id,
    )
    with pytest.raises(InvalidTransactionException):
        await InventoryTransactionService.receive(
            session, material_lot_id=lot.id, to_location_id=rack.id,
        )

    txn = await InventoryTransactionService.putaway(
        session, material_lot_id=lot.id, from_location_id=recv.id, to_location_id=rack.id,
    )
    assert txn.quantity == 1.0
    rows = (await session.execute(select(InventoryBalance))).scalars().all()
    balances = {b.location_id: b.quantity_on_hand for b in rows}
    assert balances[recv.id] == 0.0
    assert balances[rack.id] == 1.0
    assert lot.quantity_on_hand == 1.0


@pytest.mark.asyncio
async def test_unit_rejects_other_quantities_and_adjust(session):
    material = await _material(session, "EA", "unit")
    lot = await MaterialLotService.create_lot(session, material_id=material.id, lot_number="SN-3")
    recv = await _location(session, "RECV")

    with pytest.raises(InvalidTransactionException):
        await InventoryTransactionService.receive(
            session, material_lot_id=lot.id, to_location_id=recv.id, quantity=5,
        )
    await InventoryTransactionService.receive(
        session, material_lot_id=lot.id, to_location_id=recv.id,
    )
    with pytest.raises(UnitTrackedRestrictionException):
        await InventoryTransactionService.adjust(
            session, material_lot_id=lot.id, location_id=recv.id, quantity=0, reason="count",
        )
    with pytest.raises(UnitTrackedRestrictionException):
        await MaterialLotService.update_lot(session, lot.id, quantity_on_hand=3.0)


@pytest.mark.asyncio
async def test_unit_consume_defaults_to_one_and_exhausts(session):
    material = await _material(session, "EA", "unit")
    lot = await MaterialLotService.create_lot(session, material_id=material.id, lot_number="SN-4")
    recv = await _location(session, "RECV")
    await InventoryTransactionService.receive(
        session, material_lot_id=lot.id, to_location_id=recv.id,
    )

    consumption = await MaterialLotService.consume(session, lot.id)
    assert consumption.quantity_consumed == 1.0
    assert lot.status == "consumed"
    assert lot.quantity_on_hand == 0.0

    with pytest.raises(InvalidTransactionException):
        await InventoryTransactionService.receive(
            session, material_lot_id=lot.id, to_location_id=recv.id,
        )


@pytest.mark.asyncio
async def test_lot_tracked_behaviour_unchanged(session):
    material = await _material(session, "kg")
    lot = await MaterialLotService.create_lot(
        session, material_id=material.id, lot_number="LOT-1", quantity_on_hand=0.0,
    )
    recv, rack = await _location(session, "RECV"), await _location(session, "RACK")

    await InventoryTransactionService.receive(
        session, material_lot_id=lot.id, to_location_id=recv.id, quantity=10,
    )
    with pytest.raises(InvalidTransactionException):
        await InventoryTransactionService.putaway(
            session, material_lot_id=lot.id, from_location_id=recv.id, to_location_id=rack.id,
        )
    await InventoryTransactionService.putaway(
        session, material_lot_id=lot.id, from_location_id=recv.id, to_location_id=rack.id,
        quantity=4,
    )
    await InventoryTransactionService.adjust(
        session, material_lot_id=lot.id, location_id=rack.id, quantity=3, reason="count",
    )
    assert lot.quantity_on_hand == 9.0
    consumption = await MaterialLotService.consume(session, lot.id, quantity_consumed=2.5)
    assert consumption.quantity_consumed == 2.5
