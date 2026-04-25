import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

DB = 'postgresql+asyncpg://postgres:postgres@localhost:5432/mes_ai_s95'

async def m():
    e = create_async_engine(DB)
    async with AsyncSession(e) as s:
        r = await s.execute(text(
            "SELECT ps.sequence, ps.name as step_name, d.name as disposition_name, d.category "
            "FROM process_segments ps "
            "LEFT JOIN dispositions d ON d.id = ps.disposition_id "
            "JOIN operations_definitions od ON od.id = ps.route_id "
            "WHERE od.name = 'SMT Assembly Line' ORDER BY ps.sequence"
        ))
        print('STEP -> linked Disposition:')
        for row in r:
            print(' ', dict(row._mapping))


asyncio.run(m())
