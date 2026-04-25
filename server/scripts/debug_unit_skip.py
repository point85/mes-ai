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
        unit_id, order_id = u.id, u.order_id

        r = await s.execute(text(
            "SELECT od.id FROM operations_definitions od WHERE od.name = :n"
        ), {'n': ROUTE_NAME})
        route_id = r.scalar()
        print('route_id:', route_id)

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
            "SELECT step_id, entered_at, exited_at, result, disposition "
            "FROM segment_response_units WHERE unit_id = :uid ORDER BY entered_at NULLS LAST"
        ), {'uid': unit_id})
        print('\n=== UNIT HISTORY ===')
        for row in r:
            d = dict(row._mapping)
            sid = d.get('step_id')
            seq = steps_by_id.get(sid, {}).get('sequence')
            name = steps_by_id.get(sid, {}).get('name')
            print(f"  seq={seq} name={name!r} entered={d.get('entered_at')} exited={d.get('exited_at')} result={d.get('result')} disp={d.get('disposition')}")

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
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

SN = 'SN-FG-ECB-100-MOC4P5FC-001-00099'
DB = 'postgresql+asyncpg://postgres:postgres@localhost:5432/mes_ai_s95'


async def main():
    eng = create_async_engine(DB)
    async with AsyncSession(eng) as s:
        r = await s.execute(text(
            "SELECT id, serial_number, current_step_id, status, order_id "
            "FROM units WHERE serial_number = :sn"
        ), {'sn': SN})
        u = r.first()
        if not u:
            print('UNIT NOT FOUND')
            return
        print('UNIT:', dict(u._mapping))
        unit_id, order_id = u.id, u.order_id

        r = await s.execute(text("SELECT route_id, product_id, status FROM operations_requests WHERE id = :oid"), {'oid': order_id})
        order = r.first()
        print('ORDER:', dict(order._mapping) if order else None)
        route_id = order._mapping.get('route_id') if order else None

        if route_id is None:
            # check default route
            r = await s.execute(text(
                "SELECT od.id, od.name FROM operations_definitions od "
                "JOIN operations_definition_product_assignments a ON a.route_id = od.id "
                "WHERE a.product_id = :pid AND a.is_active = true AND od.is_active = true"
            ), {'pid': order._mapping.get('product_id')})
            print('candidate routes for product:')
            for row in r: print(' ', dict(row._mapping))
            return

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

        cur = u.current_step_id
        cs = steps_by_id.get(cur, {})
        print(f"\nCURRENT STEP: id={cur} seq={cs.get('sequence')} name={cs.get('name')!r} active={cs.get('is_active')}")

        r = await s.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='segment_response_units' ORDER BY ordinal_position"))
        sru_cols = [row[0] for row in r]
        order_clause = 'entered_at NULLS LAST' if 'entered_at' in sru_cols else 'created_at'

        r = await s.execute(text(
            f"SELECT * FROM segment_response_units WHERE unit_id = :uid ORDER BY {order_clause}"
        ), {'uid': unit_id})
        print('\n=== UNIT HISTORY ===')
        for row in r:
            d = dict(row._mapping)
            sid = d.get('step_id')
            seq = steps_by_id.get(sid, {}).get('sequence')
            name = steps_by_id.get(sid, {}).get('name')
            print(f"  seq={seq} name={name!r} entered={d.get('entered_at')} exited={d.get('exited_at')} result={d.get('result')} disp={d.get('disposition')}")

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
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

SN = 'SN-FG-ECB-100-MOC4P5FC-001-00099'


async def main():
    eng = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/mes_ai')
    async with AsyncSession(eng) as s:
        r = await s.execute(text(
            "SELECT id, serial_number, current_step_id, status, order_id "
            "FROM units WHERE serial_number = :sn"
        ), {'sn': SN})
        u = r.first()
        if not u:
            print('UNIT NOT FOUND')
            r2 = await s.execute(text("SELECT serial_number FROM units WHERE serial_number ILIKE :p"), {'p': '%00099%'})
            print('matches with 00099:', [row[0] for row in r2])
            return
        print('UNIT:', dict(u._mapping))
        unit_id = u.id
        order_id = u.order_id

        # operations_requests is the order table per earlier discovery
        r = await s.execute(text("SELECT * FROM operations_requests WHERE id = :oid"), {'oid': order_id})
        row = r.first()
        if row is None:
            print('ORDER NOT FOUND')
            return
        print('ORDER keys:', list(row._mapping.keys()))
        route_id = row._mapping.get('route_id')
        print('route_id:', route_id)

        r = await s.execute(text(
            "SELECT id, name, sequence, is_active, disposition_id FROM process_segments "
            "WHERE route_id = :rid ORDER BY sequence"
        ), {'rid': route_id})
        print('\n=== ROUTE STEPS ===')
        steps_by_id = {}
        for row in r:
            d = dict(row._mapping)
            steps_by_id[d['id']] = d
            print(f"  seq={d['sequence']:>4} name={d['name']!r} active={d['is_active']} disp_id={d['disposition_id']}")

        r = await s.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='segment_response_units' ORDER BY ordinal_position"))
        sru_cols = [row[0] for row in r]
        print('\nSRU cols:', sru_cols)

        r = await s.execute(text(
            "SELECT * FROM segment_response_units WHERE unit_id = :uid ORDER BY created_at"
        ), {'uid': unit_id})
        print('\n=== UNIT HISTORY ===')
        for row in r:
            d = dict(row._mapping)
            sid = d.get('step_id')
            seq = steps_by_id.get(sid, {}).get('sequence')
            name = steps_by_id.get(sid, {}).get('name')
            print(f"  seq={seq} name={name!r} entered={d.get('entered_at')} exited={d.get('exited_at')} result={d.get('result')} disp={d.get('disposition')}")

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
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

SN = 'SN-FG-ECB-100-MOC4P5FC-001-00099'

async def main():
    eng = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/mes_ai')
    async with AsyncSession(eng) as s:
        r = await s.execute(text(
            "SELECT id, serial_number, current_step_id, status, order_id "
            "FROM units WHERE serial_number = :sn"
        ), {'sn': SN})
        u = r.first()
        print('UNIT:', dict(u._mapping) if u else None)
        if not u:
            return
        unit_id = u.id
        order_id = u.order_id

        r = await s.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='operations_requests'"))
        op_cols = [row[0] for row in r]
        print('operations_requests cols:', op_cols)

        r = await s.execute(text("SELECT * FROM operations_requests WHERE id = :oid"), {'oid': order_id})
        row = r.first()
        print('ORDER:', dict(row._mapping) if row else None)
        if row is None:
            return
        route_id = row._mapping.get('route_id')

        r = await s.execute(text(
            "SELECT id, name, sequence, is_active, disposition_id FROM process_segments "
            "WHERE route_id = :rid ORDER BY sequence"
        ), {'rid': route_id})
        print('\n=== ROUTE STEPS ===')
        steps_by_id = {}
        for row in r:
            d = dict(row._mapping)
            steps_by_id[d['id']] = d
            print(d)

        r = await s.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='segment_response_units' ORDER BY ordinal_position"))
        print('\nSRU cols:', [row[0] for row in r])

        r = await s.execute(text(
            "SELECT * FROM segment_response_units WHERE unit_id = :uid ORDER BY created_at"
        ), {'uid': unit_id})
        print('\n=== UNIT HISTORY ===')
        for row in r:
            d = dict(row._mapping)
            sid = d.get('step_id')
            seq = steps_by_id.get(sid, {}).get('sequence')
            name = steps_by_id.get(sid, {}).get('name')
            print(f"seq={seq} name={name} entered={d.get('entered_at')} exited={d.get('exited_at')} result={d.get('result')} disp={d.get('disposition')}")

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
            print(f"{f.get('sequence')}({f.get('name')}) -> {t.get('sequence')}({t.get('name')}) cond={d['condition']} label={d['label']} pri={d['priority']} default={d['is_default']} active={d['is_active']}")

asyncio.run(main())
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

SN = 'SN-FG-ECB-100-MOC4P5FC-001-00099'

async def main():
    eng = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/mes_ai')
    async with AsyncSession(eng) as s:
        r = await s.execute(text(
            "SELECT id, serial_number, current_step_id, status, production_order_id "
            "FROM units WHERE serial_number = :sn"
        ), {'sn': SN})
        u = r.first()
        print('UNIT:', dict(u._mapping) if u else None)
        if not u:
            return
        unit_id = u.id
        order_id = u.production_order_id

        r = await s.execute(text(
            "SELECT ps.id as step_id, ps.name, ps.sequence, ps.is_active, ps.disposition_id "
            "FROM production_orders po "
            "JOIN process_segments ps ON ps.route_id = po.route_id "
            "WHERE po.id = :oid ORDER BY ps.sequence"
        ), {'oid': order_id})
        print('\n=== ROUTE STEPS ===')
        for row in r:
            print(dict(row._mapping))

        r = await s.execute(text(
            "SELECT sr.step_id, ps.name, ps.sequence, sr.entered_at, sr.exited_at, sr.result, sr.disposition "
            "FROM segment_responses_unit sr JOIN process_segments ps ON ps.id = sr.step_id "
            "WHERE sr.unit_id = :uid ORDER BY sr.entered_at"
        ), {'uid': unit_id})
        print('\n=== UNIT HISTORY ===')
        for row in r:
            print(dict(row._mapping))

        r = await s.execute(text(
            "SELECT fs.sequence as from_seq, fs.name as from_name, ts.sequence as to_seq, ts.name as to_name, "
            "psd.condition, psd.label, psd.priority, psd.is_default, psd.is_active, psd.disposition_id "
            "FROM process_segment_dependencies psd "
            "JOIN process_segments fs ON fs.id = psd.from_step_id "
            "JOIN process_segments ts ON ts.id = psd.to_step_id "
            "WHERE fs.route_id = (SELECT route_id FROM production_orders WHERE id = :oid) "
            "ORDER BY fs.sequence, psd.priority DESC"
        ), {'oid': order_id})
        print('\n=== TRANSITIONS ===')
        for row in r:
            print(dict(row._mapping))

asyncio.run(main())
