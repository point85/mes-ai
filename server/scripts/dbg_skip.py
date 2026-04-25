import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

SN = 'SN-FG-ECB-100-MOC4P5FC-001-00099'
DB = 'postgresql+asyncpg://postgres:postgres@localhost:5432/mes_ai_s95'
ROUTE_NAME = 'SMT Assembly Line'


async def main():
    eng = create_async_engine(DB)
    async with AsyncSession(eng) as s:
        r = await s.execute(text(
            "SELECT id, serial_number, current_step_id, status, order_id "
            "FROM units WHERE serial_number = :sn"
        ), {'sn': SN})
        u = r.first()
        print('UNIT:', dict(u._mapping))
        unit_id, _ = u.id, u.order_id

        r = await s.execute(text(
            "SELECT id FROM operations_definitions WHERE name = :n"
        ), {'n': ROUTE_NAME})
        route_id = r.scalar()

        r = await s.execute(text(
            "SELECT id, name, sequence, is_active, disposition_id FROM process_segments "
            "WHERE route_id = :rid ORDER BY sequence"
        ), {'rid': route_id})
        steps_by_id = {}
        print('\n=== ROUTE STEPS ===')
        for row in r:
            d = dict(row._mapping)
            steps_by_id[d['id']] = d
            print(f"  seq={d['sequence']:>4} name={d['name']!r} active={d['is_active']} disp_id={d['disposition_id']}")

        cs = steps_by_id.get(u.current_step_id, {})
        print(f"\nCURRENT STEP: seq={cs.get('sequence')} name={cs.get('name')!r}")

        r = await s.execute(text(
            "SELECT step_id, equipment_id, entered_at, exited_at, result "
            "FROM segment_response_units WHERE unit_id = :uid ORDER BY entered_at NULLS LAST"
        ), {'uid': unit_id})
        print('\n=== UNIT HISTORY ===')
        for row in r:
            d = dict(row._mapping)
            sid = d.get('step_id')
            seq = steps_by_id.get(sid, {}).get('sequence')
            name = steps_by_id.get(sid, {}).get('name')
            print(f"  seq={seq} name={name!r} entered={d.get('entered_at')} exited={d.get('exited_at')} result={d.get('result')} equip={d.get('equipment_id')}")

        r = await s.execute(text(
            "SELECT psd.from_step_id, psd.to_step_id, psd.condition, psd.label, psd.priority, psd.is_default, psd.is_active "
            "FROM process_segment_dependencies psd "
            "JOIN process_segments fs ON fs.id = psd.from_step_id "
            "WHERE fs.route_id = :rid ORDER BY fs.sequence, psd.priority DESC"
        ), {'rid': route_id})
        print('\n=== TRANSITIONS ===')
        for row in r:
            d = dict(row._mapping)
            f = steps_by_id.get(d['from_step_id'], {})
            t = steps_by_id.get(d['to_step_id'], {})
            print(f"  {f.get('sequence')}({f.get('name')}) -> {t.get('sequence')}({t.get('name')}) cond={d['condition']} label={d['label']!r} pri={d['priority']} default={d['is_default']} active={d['is_active']}")


asyncio.run(main())
