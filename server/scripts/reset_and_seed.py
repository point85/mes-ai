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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("reset")


def _get_db_info() -> tuple[str, str, str]:
    """Return (maint_url, db_name, db_name_for_log) derived from settings."""
    from sqlalchemy.engine.url import make_url
    from mes.config import settings

    url = make_url(settings.DATABASE_URL)
    db_name = url.database or "mes_ai"
    user = url.username or "postgres"
    pwd = str(url.password or "postgres")
    host = url.host or "localhost"
    port = url.port or 5432
    maint_url = f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/postgres"
    return maint_url, db_name, f"{host}:{port}/{db_name}"


async def drop_and_recreate_schema() -> None:
    """Drop-and-recreate the application database itself. Connects to the
    maintenance `postgres` database to avoid the can't-drop-self error.
    """
    maint_url, db_name, db_label = _get_db_info()
    engine = create_async_engine(maint_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as c:
            log.info("Terminating other connections to %s ...", db_label)
            await c.execute(text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :db AND pid <> pg_backend_pid()"
            ).bindparams(db=db_name))
            log.info("Dropping database %s (if exists) ...", db_name)
            await c.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
            log.info("Creating database %s ...", db_name)
            await c.execute(text(f'CREATE DATABASE "{db_name}"'))
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
    from mes.core.uom.seed import get_builtin_scalar_dicts, get_builtin_composite_dicts_typed

    from mes.core.demo.service import (
        seed_electronics_erp_data,
        seed_electronics_plant_data,
        seed_erp_data,
        seed_plant_data,
    )
    from mes.framework.auth.service import AuthService

    async with async_session_factory() as session:
        log.info("Seeding built-in UoMs ...")
        from sqlalchemy import select

        existing_scalar_rows = await session.execute(
            select(UnitOfMeasure.symbol, UnitOfMeasure.id, UnitOfMeasure.uom_type)
            .where(UnitOfMeasure.uom_class == "scalar")
        )
        existing_scalars: dict[str, tuple] = {
            row.symbol: (row.id, row.uom_type) for row in existing_scalar_rows
        }
        new_scalars = [
            UnitOfMeasure(**d)
            for d in get_builtin_scalar_dicts()
            if d["symbol"] not in existing_scalars
        ]
        if new_scalars:
            session.add_all(new_scalars)
            await session.flush()
        symbol_to_uom = {
            **existing_scalars,
            **{u.symbol: (u.id, u.uom_type) for u in new_scalars},
        }

        existing_composite_syms = {
            row[0] for row in await session.execute(
                select(UnitOfMeasure.symbol)
                .where(UnitOfMeasure.uom_class.in_(["quotient", "power"]))
            )
        }
        new_composites = [
            UnitOfMeasure(**d)
            for d in get_builtin_composite_dicts_typed(symbol_to_uom)
            if d["symbol"] not in existing_composite_syms
        ]
        if new_composites:
            session.add_all(new_composites)
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

    async with async_session_factory() as session:
        log.info("Seeding default auth roles ...")
        await AuthService.seed_default_roles(session)
        log.info("Seeding default admin user ...")
        await AuthService.seed_admin_user(session)
        log.info("Seeding demo users (CPG + SMT lines) ...")
        await AuthService.seed_demo_users(session)

    log.info("Seed complete.")


async def main() -> None:
    await drop_and_recreate_schema()
    run_alembic_upgrade()
    await seed_all()


if __name__ == "__main__":
    asyncio.run(main())
