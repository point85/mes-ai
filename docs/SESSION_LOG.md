# MES AI -- Session Log

> This file is the chronological narrative of the **current** project sessions.
> **AI agents**: Read [PROJECT_STATE.json](PROJECT_STATE.json) first for structured state, then this log for recent context.
> **Humans**: This file provides oversight visibility into what the AI did each session.
>
> Older sessions live in [archive/](archive/). When this file grows unwieldy, archive it (e.g., `archive/SESSION_LOG_<YYYY-MM-DD>.md`) and reset with a fresh carry-over header.

---

## Carry-over from previous log

Full history through S049 is archived at [archive/SESSION_LOG_2026-05-12.md](archive/SESSION_LOG_2026-05-12.md).
Earlier history (S044-S048) is at [archive/SESSION_LOG_2026-05-06.md](archive/SESSION_LOG_2026-05-06.md).
Earlier history (S001-S038) is at [archive/SESSION_LOG_2026-04-25.md](archive/SESSION_LOG_2026-04-25.md).
Authoritative project state is in [PROJECT_STATE.json](PROJECT_STATE.json).

### Project state at reset (2026-05-12)

- **Phases complete**: P1 Survey, P2 Architecture, P3 Core Server (all 5 layers), P4 Integration Adapters, P5 Clients (DT/RT/ERP/Equipment simulators), P6 Schema/UX consolidation.
- **Current focus**: Post-P6 polish, SQA harness.
- **Active database**: `mes_ai_sqa` on `localhost:5432`.
- **Alembic head**: single consolidated baseline `4b608427bd14` (63 tables).
- **Server**: FastAPI/uvicorn on port 8082. Start: `.\run-server.ps1 PostgreSQL mes_ai_sqa`.
- **Clients**: DT-CLIENT port 5173, RT-CLIENT 5176, ERP Sim 5174, Equipment Sim 5175.

### Recently shipped (S044-S049 highlights)

- **S044**: Removed MySQL/CockroachDB/DB2; rebased Alembic to single baseline; cross-dialect env.py + script.py.mako.
- **S045**: DT-CLIENT + RT-CLIENT routing model refactor (removed StepTransition; added input_dispositions, output_dispositions, is_initial_step).
- **S046**: ERP Simulator seeding and order-queue plumbing verification.
- **S047-S048**: order_processors.py multi-route crash fix; ERP Sim UI sweep (route_id, API endpoint, UoM, lot dropdown).
- **S049**: UoM type system expanded to 10 types; 6 Alembic migrations applied; UoMFormDialog bug sweep (5 fixes); soft-delete recreation bug fixed.

### Infrastructure changes (S049 session)

- **Docker removed**: all Docker Compose and Dockerfile artefacts deleted.
- **run-server.ps1 / run-server.sh**: auto-detects empty database and stamps Alembic before upgrade; sets MES_LOG_FILE=mes_server_<port>.log per instance.
- **run-client.ps1 / run-client.sh**: -ServerUrl / --server-url option; sets MES_SERVER_URL for Vite proxy.
- **All vite.config.ts files**: read MES_SERVER_URL (default http://localhost:8082) for proxy target.
- **server/.env + alembic.ini**: updated to mes_ai_sqa.
- **Alembic**: consolidated to single baseline migration 20260512_1519_4b608427bd14_baseline.py (63 tables).

### Pending deferred work

- Verify UoM create/edit/delete round-trip in browser (all classes, all types).
- Smoke-test ERP Sim -> create order -> consumption lot dropdown.
- SQA harness bootstrap (see SQA/SQA_TESTING.md).

---
