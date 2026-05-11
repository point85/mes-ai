"""
Initialize a SQLite database for the MES server (bypasses Alembic).

Used by entrypoint.sh when MES_DATABASE_URL starts with 'sqlite'.
Creates all tables via SQLAlchemy metadata.create_all() and seeds built-in
units of measure. Safe to run repeatedly — create_all is idempotent (uses
IF NOT EXISTS) and the UoM seed checks for existing data.

Usage:
    cd server
    MES_DATABASE_URL=sqlite+aiosqlite:///./mes_test.db python scripts/init_sqlite.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure src/ is on the import path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Import ALL model modules so Base.metadata has every table registered
# (mirrors the import block in alembic/env.py)
import mes.framework.auth.models  # noqa: F401
import mes.framework.plugin.models  # noqa: F401
import mes.core.physical_model.models  # noqa: F401
import mes.core.product_def.models  # noqa: F401
import mes.core.uom.models  # noqa: F401
import mes.core.operations.models  # noqa: F401
import mes.core.wip.models  # noqa: F401
import mes.core.material.models  # noqa: F401
import mes.core.data_collection.models  # noqa: F401
import mes.core.inventory.models  # noqa: F401
import mes.core.performance.models  # noqa: F401
import mes.adapters.erp.queue  # noqa: F401
import mes.adapters.erp.inbound_queue  # noqa: F401
import mes.core.work_schedule.models  # noqa: F401

from mes.framework.db.base import Base
from mes.framework.db.session import engine, async_session_factory
from mes.core.uom.models import UnitOfMeasure
from mes.core.uom.seed import get_builtin_scalar_dicts, get_builtin_composite_dicts_typed
from sqlalchemy import select


async def init() -> None:
    # Create all tables (IF NOT EXISTS — idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created.")

    # Seed built-in units of measure
    async with async_session_factory() as session:
        result = await session.execute(select(UnitOfMeasure).limit(1))
        if result.scalars().first():
            print("UoM table already has data — skipping seed.")
            return

        base_units = [UnitOfMeasure(**d) for d in get_builtin_scalar_dicts()]
        session.add_all(base_units)
        await session.flush()

        symbol_to_uom = {u.symbol: (u.id, u.uom_type) for u in base_units}
        composite_units = [UnitOfMeasure(**d) for d in get_builtin_composite_dicts_typed(symbol_to_uom)]
        session.add_all(composite_units)

        await session.commit()
        print(f"Seeded {len(base_units)} scalar + {len(composite_units)} composite built-in units of measure.")


if __name__ == "__main__":
    asyncio.run(init())
