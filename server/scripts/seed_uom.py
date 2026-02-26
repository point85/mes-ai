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
from mes.core.uom.seed import get_builtin_unit_dicts
from sqlalchemy import select


async def seed() -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(UnitOfMeasure).limit(1))
        if result.scalars().first():
            print("UoM table already has data — skipping seed.")
            return
        units = [UnitOfMeasure(**d) for d in get_builtin_unit_dicts()]
        session.add_all(units)
        await session.commit()
        print(f"Seeded {len(units)} built-in units of measure.")


if __name__ == "__main__":
    asyncio.run(seed())
