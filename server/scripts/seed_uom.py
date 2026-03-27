"""
Seed the database with built-in units of measure.

Usage:
    cd server
    python scripts/seed_uom.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure src/ is on the import path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mes.framework.db.session import async_session_factory
from mes.core.uom.models import UnitOfMeasure
from mes.core.uom.seed import get_builtin_unit_dicts, get_builtin_rate_unit_dicts
from sqlalchemy import select


async def seed() -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(UnitOfMeasure).limit(1))
        if result.scalars().first():
            print("UoM table already has data — skipping seed.")
            return

        # Pass 1: base units
        base_units = [UnitOfMeasure(**d) for d in get_builtin_unit_dicts()]
        session.add_all(base_units)
        await session.flush()

        # Build symbol→id map for rate UoM references
        symbol_to_id = {u.symbol: u.id for u in base_units}

        # Pass 2: rate units
        rate_units = [UnitOfMeasure(**d) for d in get_builtin_rate_unit_dicts(symbol_to_id)]
        session.add_all(rate_units)

        await session.commit()
        print(f"Seeded {len(base_units)} base + {len(rate_units)} rate built-in units of measure.")


if __name__ == "__main__":
    asyncio.run(seed())
