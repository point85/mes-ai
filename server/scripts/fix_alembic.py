"""Quick script to fix alembic_version table."""
import asyncio
import asyncpg


async def main():
    conn = await asyncpg.connect(
        "postgresql://postgres:postgres@localhost:5432/mes_ai_s95"
    )
    rows = await conn.fetch("SELECT version_num FROM alembic_version")
    print("Current:", rows)
    await conn.execute(
        "UPDATE alembic_version SET version_num = '4c0016b2fcbc'"
    )
    rows = await conn.fetch("SELECT version_num FROM alembic_version")
    print("Updated:", rows)
    await conn.close()


asyncio.run(main())
