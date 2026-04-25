"""One-shot DB reset for the demo environment.

1. Terminate other connections to the mes_ai database.
2. DROP SCHEMA public CASCADE; CREATE SCHEMA public.
3. Run `alembic upgrade head` (sync).
4. Seed CPG ERP + plant, Electronics ERP + plant.

Usage (from c:\\dev\\mes_ai\\server):
    python scripts/reset_and_seed.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/mes_ai_s95"
DB_NAME = "mes_ai_s95"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("reset")


async def drop_and_recreate_schema() -> None:
    """Drop-and-recreate the application database itself. Connects to the
    maintenance `postgres` database to avoid the can't-drop-self error.
    """
    maint_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    engine = create_async_engine(maint_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as c:
            log.info("Terminating other connections to %s ...", DB_NAME)
            await c.execute(text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :db AND pid <> pg_backend_pid()"
            ).bindparams(db=DB_NAME))
            log.info("Dropping database %s (if exists) ...", DB_NAME)
            await c.execute(text(f'DROP DATABASE IF EXISTS "{DB_NAME}"'))
            log.info("Creating database %s ...", DB_NAME)
            await c.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
            log.info("Database reset complete.")
    finally:
        await engine.dispose()


def run_alembic_upgrade() -> None:
    log.info("Running alembic upgrade head ...")
    server_dir = Path(__file__).resolve().parent.parent
    alembic_exe = Path(sys.executable).parent / ("alembic.exe" if os.name == "nt" else "alembic")
    subprocess.run(
        [str(alembic_exe), "upgrade", "head"],
        cwd=str(server_dir), check=True,
    )
    log.info("Alembic upgrade complete.")


async def seed_all() -> None:
    # Pre-import every model package so SQLAlchemy relationship string
    # references (e.g. "Unit") resolve before we start querying.
    import importlib
    import pkgutil

    import mes.core as _core_pkg

    for mod in pkgutil.iter_modules(_core_pkg.__path__):
        try:
            importlib.import_module(f"mes.core.{mod.name}.models")
        except ModuleNotFoundError:
            continue

    from mes.framework.db import async_session_factory

    from mes.core.uom.models import UnitOfMeasure
    from mes.core.uom.seed import get_builtin_rate_unit_dicts, get_builtin_unit_dicts

    from mes.core.demo.service import (
        seed_electronics_erp_data,
        seed_electronics_plant_data,
        seed_erp_data,
        seed_plant_data,
    )

    async with async_session_factory() as session:
        log.info("Seeding built-in UoMs ...")
        base_units = [UnitOfMeasure(**d) for d in get_builtin_unit_dicts()]
        session.add_all(base_units)
        await session.flush()
        symbol_to_id = {u.symbol: u.id for u in base_units}
        rate_units = [UnitOfMeasure(**d) for d in get_builtin_rate_unit_dicts(symbol_to_id)]
        session.add_all(rate_units)
        await session.commit()

    async with async_session_factory() as session:
        log.info("Seeding CPG ERP data ...")
        await seed_erp_data(session)
        log.info("Seeding CPG plant data ...")
        await seed_plant_data(session)
        log.info("Seeding Electronics ERP data ...")
        await seed_electronics_erp_data(session)
        log.info("Seeding Electronics plant data ...")
        await seed_electronics_plant_data(session)
    log.info("Seed complete.")


async def main() -> None:
    await drop_and_recreate_schema()
    run_alembic_upgrade()
    await seed_all()


if __name__ == "__main__":
    asyncio.run(main())
