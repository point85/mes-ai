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
from mes.core.uom.seed import get_builtin_scalar_dicts, get_builtin_composite_dicts_typed
from sqlalchemy import select


async def seed() -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(UnitOfMeasure).limit(1))
        if result.scalars().first():
            print("UoM table already has data — skipping seed.")
            return

        # Pass 1: scalar units
        base_units = [UnitOfMeasure(**d) for d in get_builtin_scalar_dicts()]
        session.add_all(base_units)
        await session.flush()

        # Build symbol→(id, type) map for composite UoM references
        symbol_to_uom = {u.symbol: (u.id, u.uom_type) for u in base_units}

        # Pass 2: composite units (quotient + power)
        composite_units = [UnitOfMeasure(**d) for d in get_builtin_composite_dicts_typed(symbol_to_uom)]
        session.add_all(composite_units)

        await session.commit()
        print(f"Seeded {len(base_units)} scalar + {len(composite_units)} composite built-in units of measure.")


if __name__ == "__main__":
    asyncio.run(seed())
