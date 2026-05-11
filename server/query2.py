import asyncio
import sys
sys.path.insert(0, 'src')
import os
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/mes_ai_s95')

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine(os.environ['DATABASE_URL'])
    async with engine.connect() as conn:
        rows = await conn.execute(text("""
            SELECT symbol, name, uom_type, uom_class, left_uom_id, right_uom_id
            FROM units_of_measure
            WHERE symbol IN ('L', 'mL', 'fl oz', 'L/h', 'L/min', 'mL/h', 'mm/s', 'mm/min', 'ft/s', 'ft/min', 'ft/h')
            ORDER BY symbol
        """))
        for r in rows:
            print(r)

asyncio.run(main())
