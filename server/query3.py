import asyncio, os, sys
sys.path.insert(0, 'src')
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/mes_ai_s95')
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine(os.environ['DATABASE_URL'])
    async with engine.connect() as conn:
        rows = await conn.execute(text("""
            SELECT id, symbol, name, uom_type, uom_class, is_builtin
            FROM units_of_measure
            WHERE name ILIKE '%brix%'
               OR name ILIKE '%pH%'
               OR name ILIKE '%colony%'
               OR name ILIKE '%newton%'
               OR name ILIKE '%ampere%'
               OR name ILIKE '%pascal%'
               OR name ILIKE '%volt%'
            ORDER BY name
        """))
        for r in rows:
            print(r)

asyncio.run(main())
