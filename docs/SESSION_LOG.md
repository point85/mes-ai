# MES AI -- Session Log

> This file is the chronological narrative of the **current** project sessions.
> **AI agents**: Read [PROJECT_STATE.json](PROJECT_STATE.json) first for structured state, then this log for recent context.
> **Humans**: This file provides oversight visibility into what the AI did each session.
>
> Older sessions live in [archive/](archive/). When this file grows unwieldy, archive it (e.g., `archive/SESSION_LOG_<YYYY-MM-DD>.md`) and reset with a fresh carry-over header.

---

## Carry-over from previous log

Full history through S043 is archived at [archive/SESSION_LOG_2026-05-06.md](archive/SESSION_LOG_2026-05-06.md).
Earlier history (S001-S038) is at [archive/SESSION_LOG_2026-04-25.md](archive/SESSION_LOG_2026-04-25.md).
Authoritative project state is in [PROJECT_STATE.json](PROJECT_STATE.json).

### Project state at reset (2026-05-06)

- **Phases complete**: P1 Survey, P2 Architecture, P3 Core Server (all 5 layers), P4 Integration Adapters, P5 Clients (DT/RT/ERP/Equipment simulators), P6 Schema/UX consolidation.
- **Current focus**: Post-P6 polish; P7 (Testing & CI) not yet started.
- **Active database**: `mes_ai_s95` on `localhost:5432`.
- **Server**: FastAPI/uvicorn on port 8082. Start: `cd server && uvicorn mes.main:app --reload --port 8082`.
- **Clients**: DT-CLIENT port 5173, RT-CLIENT 5176, ERP Sim 5174, Equipment Sim 5175.
- **Last Alembic head**: `5aefea3fbea4` (disposition junction tables + `is_initial_step`).

### Recently shipped (S039-S043 highlights)

- **S039** (Apr 25): DB rename `mes_ai` -> `mes_ai_s95`; DISPATCH x WIP-TRACK double-move race fixed.
- **S040** (Apr 25): `SegmentEquipmentRequirement` UI verified fully shipped.
- **S041** (Apr 28): RT-CLIENT UX improvements; demo seeders made additive; routing engine terminal-step fix.
- **S042** (Apr 30): Major routing model refactor -- replaced `ProcessSegmentDependency` with per-step `input_disposition`/`output_disposition` junction tables; `is_initial_step` flag; routing engine rewritten; 1840 unit tests passing.
- **S043** (May 6): Hardcoded plugin/log paths (removed `PLUGIN_DIR`, `PLUGIN_USER_DIR`, `LOG_DIR` from Settings); DT-CLIENT Admin > Settings page; Demo seed pages extracted to `/demos/cpg` and `/demos/electronics`; Docker Compose installer (`docker-compose.yml`, `install.ps1`, `install.sh`, server/client Dockerfiles, shared `nginx.conf`).

### Architecture: routing model (as of S042)

Each `ProcessSegment` (step) has:
- `input_dispositions: list[Disposition]` -- step accepts WIP arriving with one of these dispositions.
- `output_dispositions: list[Disposition]` -- step emits one of these dispositions on completion.
- `is_initial_step: bool` -- authoritative entry-point flag.

Routing rules at runtime:
- **0 outputs** => terminal (lot/unit completed).
- **1 output** => auto-routed; UI must not show disposition picker.
- **N outputs** => caller must supply a disposition; `AmbiguousDispositionError` if not provided.

### Pending deferred work

**DT-CLIENT + RT-CLIENT frontend (broken since S042 backend refactor)**:
1. `clients/design_time/src/types/productDef.ts` -- replace `StepTransition*` types with `input_dispositions`/`output_dispositions`/`is_initial_step`.
2. `clients/design_time/src/api/productDef.ts` -- remove transition CRUD API calls.
3. `clients/design_time/src/hooks/useProductDef.ts` -- remove transition mutation hooks.
4. `clients/design_time/src/pages/products/StepFormDialog.tsx` -- two Disposition multi-selects + `is_initial_step` checkbox.
5. `clients/design_time/src/pages/products/TransitionFormDialog.tsx` -- DELETE.
6. `clients/design_time/src/pages/products/RouteFlowDiagram.tsx` -- render edges from output->input disposition matching.
7. `clients/run_time/src/components/StepProcessingPanel.tsx` -- disposition picker only when N outputs.

**Other**:
- P7 -- CI pipeline + `server/tests/integration/` + mock simulation layer.
- Docker installer end-to-end test (requires Docker Desktop).

---
