"""
Alembic environment configuration for MES AI.

Uses async SQLAlchemy engine (asyncpg) for both autogenerate and
online migration execution.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from mes.config import settings

# -- Import ALL model modules so Base.metadata has every table --
import mes.framework.auth.models  # noqa: F401
import mes.core.physical_model.models  # noqa: F401
import mes.core.product_def.models  # noqa: F401
import mes.core.uom.models  # noqa: F401
import mes.core.production.models  # noqa: F401
import mes.core.wip.models  # noqa: F401
import mes.core.material.models  # noqa: F401
import mes.core.data_collection.models  # noqa: F401
import mes.core.quality.models  # noqa: F401
import mes.core.performance.models  # noqa: F401
import mes.adapters.erp.queue  # noqa: F401

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
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — uses a live async connection."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
