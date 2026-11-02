"""Ship transaction for finished (WIP transferred) inventory."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.core.inventory.exceptions import InvalidTransactionException
from mes.core.inventory.models import InventoryBalance
from mes.core.inventory.service import InventoryTransactionService
from mes.core.material.service import MaterialLotService
from mes.core.wip.models import Lot, Unit
from mes.core.wip.transfer import transfer_to_inventory
from mes.framework.api.pagination import PaginationParams

from test_wip_transfer import _complete_step, _setup, session  # noqa: F401


async def _finished_unit(session: AsyncSession):  # noqa: F811
    product, order, _material, location = await _setup(session, "EA")
    unit = Unit(serial_number="SN-S1", order_id=order.id, product_id=product.id, status="completed")
    session.add(unit)
    await session.flush()
    await _complete_step(session, "unit", unit, order, location.id)
    lot, _qty, _loc = await transfer_to_inventory(session, "unit", unit.id)
    return lot, location


async def _finished_lot(session: AsyncSession):  # noqa: F811
    product, order, _material, location = await _setup(
        session, "kg", product_type="process",
    )
    wip_lot = Lot(
        lot_number="LN-SHIP-1",
        order_id=order.id,
        product_id=product.id,
        quantity=7,
        status="queued",
    )
    session.add(wip_lot)
    await session.flush()
    await _complete_step(session, "lot", wip_lot, order, location.id)
    material_lot, _, _ = await transfer_to_inventory(session, "lot", wip_lot.id)
    return material_lot, location


@pytest.mark.asyncio
async def test_transferred_item_is_finished_and_ships(session):  # noqa: F811
    lot, location = await _finished_unit(session)
    assert lot.status == "finished"

    txn = await InventoryTransactionService.ship(
        session, material_lot_id=lot.id, from_location_id=location.id, reason="BOL 42",
    )
    assert (
        txn.transaction_type,
        txn.from_location_id,
        txn.to_location_id,
        txn.quantity,
        txn.reason,
    ) == ("ship", location.id, None, 1.0, "BOL 42")
    assert lot.status == "shipped" and lot.quantity_on_hand == 0

    lots, _, _ = await MaterialLotService.list_lots(session, PaginationParams(limit=50))
    assert lot.id not in [item.id for item in lots]

    with pytest.raises(InvalidTransactionException):
        await InventoryTransactionService.ship(
            session, material_lot_id=lot.id, from_location_id=location.id,
        )


@pytest.mark.asyncio
async def test_process_lot_ships_full_quantity(session):  # noqa: F811
    lot, location = await _finished_lot(session)
    assert lot.tracking_method == "lot"
    assert lot.quantity_on_hand == 7.0

    txn = await InventoryTransactionService.ship(
        session, material_lot_id=lot.id, from_location_id=location.id,
    )

    assert txn.quantity == 7.0
    assert lot.status == "shipped"
    assert lot.quantity_on_hand == 0.0
    balance = (
        await session.execute(
            select(InventoryBalance).where(
                InventoryBalance.material_lot_id == lot.id,
                InventoryBalance.location_id == location.id,
            ),
        )
    ).scalar_one()
    assert balance.quantity_on_hand == 0.0


@pytest.mark.asyncio
async def test_non_finished_item_cannot_ship(session):  # noqa: F811
    lot, location = await _finished_unit(session)
    lot.status = "available"
    with pytest.raises(InvalidTransactionException):
        await InventoryTransactionService.ship(
            session, material_lot_id=lot.id, from_location_id=location.id,
        )

@pytest.mark.asyncio
async def test_genealogy_includes_transfer_and_ship(session):  # noqa: F811
    from mes.core.genealogy.service import GenealogyService

    lot, location = await _finished_unit(session)
    unit = (await session.execute(select(Unit).where(Unit.serial_number == "SN-S1"))).scalar_one()
    await InventoryTransactionService.ship(
        session, material_lot_id=lot.id, from_location_id=location.id, reason="BOL 42",
    )
    rec = await GenealogyService.get_unit_genealogy(session, unit.id)
    assert [t.transaction_type for t in rec.inventory_transactions] == ["receive", "ship"]
    assert rec.inventory_transactions[0].to_location == location.name
