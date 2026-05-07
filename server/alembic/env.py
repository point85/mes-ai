"""
Alembic environment configuration for MES AI.

Supports all three database backends:
  - PostgreSQL + asyncpg  → async engine path
  - MSSQL     + pyodbc    → sync engine path (pyodbc has no async support)
  - Oracle    + oracledb  → sync engine path

The backend is detected from the DATABASE_URL driver component.
Async drivers: asyncpg
Sync drivers:  pyodbc, oracledb (everything else)
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from mes.config import settings

# -- Import ALL model modules so Base.metadata has every table --
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

# Alembic Config object — gives access to alembic.ini values
config = context.config

# Set the SQLAlchemy URL from application settings (overrides alembic.ini)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate' support
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migrations  (emit SQL without a live database connection)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits raw SQL to stdout/file."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations  (connect to the database)
# ---------------------------------------------------------------------------

def do_run_migrations(connection: Connection) -> None:
    """Configure Alembic context with the given connection and run."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


def _url_is_async(url: str) -> bool:
    """Return True if the URL uses an async driver (asyncpg)."""
    return "asyncpg" in url


async def run_async_migrations() -> None:
    """Create an async engine and run migrations inside a connection."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_sync_migrations() -> None:
    """Create a sync engine and run migrations — used for pyodbc (MSSQL) and
    oracledb (Oracle) which do not support asyncio."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode, choosing sync vs async based on driver."""
    url = config.get_main_option("sqlalchemy.url")
    if _url_is_async(url):
        asyncio.run(run_async_migrations())
    else:
        run_sync_migrations()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
