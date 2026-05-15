"""Normalize demo inventory before RT SQA audits.

The RT inventory and WIP audits consume seeded demo stock. This script tops up
the seeded demo material lots before a test run so repeated audits do not
require a full DB reseed.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict

from sqlalchemy import select

from mes.core.demo.cpg_data import MATERIAL_LOTS as CPG_MATERIAL_LOTS
from mes.core.demo.electronics_data import MATERIAL_LOTS as ELECTRONICS_MATERIAL_LOTS
from mes.core.inventory.models import InventoryBalance, StorageLocation
from mes.core.material.models import MaterialLot
from mes.framework.db import async_session_factory


SEEDED_TARGETS = {
    lot["lot_number"]: float(lot["quantity_on_hand"])
    for lot in [*CPG_MATERIAL_LOTS, *ELECTRONICS_MATERIAL_LOTS]
}


async def normalize_inventory() -> dict[str, int]:
    async with async_session_factory() as session:
        lot_rows = await session.execute(
            select(MaterialLot)
            .where(
                MaterialLot.lot_number.in_(tuple(SEEDED_TARGETS.keys())),
                MaterialLot.is_active.is_(True),
            )
            .order_by(MaterialLot.lot_number)
        )
        lots = lot_rows.scalars().all()

        balance_rows = await session.execute(
            select(InventoryBalance).where(
                InventoryBalance.material_lot_id.in_([lot.id for lot in lots]),
                InventoryBalance.is_active.is_(True),
            )
        )
        balances = balance_rows.scalars().all()

        location_rows = await session.execute(
            select(StorageLocation)
            .where(StorageLocation.is_active.is_(True))
            .order_by(StorageLocation.code)
        )
        locations = location_rows.scalars().all()
        fallback_location = next(
            (location for location in locations if "RECV" not in location.code.upper()),
            locations[0] if locations else None,
        )

        balances_by_lot: dict[str, list[InventoryBalance]] = defaultdict(list)
        for balance in balances:
            balances_by_lot[str(balance.material_lot_id)].append(balance)

        lots_topped_up = 0
        balances_created = 0
        balances_topped_up = 0

        for lot in lots:
            target_qty = SEEDED_TARGETS[lot.lot_number]

            if lot.quantity_on_hand < target_qty or lot.status != "available":
                lot.quantity_on_hand = target_qty
                lot.status = "available"
                lots_topped_up += 1

            lot_balances = balances_by_lot.get(str(lot.id), [])
            total_balance = sum(float(balance.quantity_on_hand) for balance in lot_balances)
            if total_balance >= target_qty:
                continue

            delta = target_qty - total_balance
            target_balance = None
            if lot_balances:
                target_balance = max(lot_balances, key=lambda balance: float(balance.quantity_on_hand))
            elif fallback_location is not None:
                target_balance = InventoryBalance(
                    material_lot_id=lot.id,
                    location_id=fallback_location.id,
                    quantity_on_hand=0.0,
                    quantity_reserved=0.0,
                )
                session.add(target_balance)
                balances_created += 1

            if target_balance is not None:
                target_balance.quantity_on_hand = float(target_balance.quantity_on_hand) + delta
                balances_topped_up += 1

        await session.commit()
        return {
            "lots_seen": len(lots),
            "lots_topped_up": lots_topped_up,
            "balances_created": balances_created,
            "balances_topped_up": balances_topped_up,
        }


def main() -> None:
    print(asyncio.run(normalize_inventory()))


if __name__ == "__main__":
    main()