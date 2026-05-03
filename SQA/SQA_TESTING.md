# SQA Testing — Design Document

**Status:** Design (pre-implementation)
**Author:** AI Coding Agent
**Date:** 2026-05-03
**MES Version Targeted:** 1.0.0

This document captures the design of the **autonomous SQA agent** system for the MES. It addresses each of the six considerations from the request, makes a recommendation per item, and defines the folder layout and templates that subsequent implementation tasks will follow. **No code is changed by this document** — it is a contract for the next set of tasks.

The MES is intended to be designed, coded, and tested entirely by AI. The SQA agent is therefore designed under the same constraint: tests are produced and maintained by an AI from documentation, and re-executed deterministically thereafter.

---

## 0. Goals

1. Validate every shipping module (server REST, DT-CLIENT, RT-CLIENT, ERP Simulator, Equipment Simulator) against the requirements documented in `docs/` and the OpenAPI spec — *not* against the source code.
2. Run autonomously and unattended; produce machine- and human-readable status; raise GitHub issues on failure.
3. Minimise long-term token cost: an agent writes/repairs tests; deterministic runners (pytest/Playwright) re-execute them at zero token cost.
4. Be repeatable both during development (against the working tree) and at release time (against a tagged release candidate).

---

## 1. Technology Stack — Token-Cost Optimised

**Recommendation: pytest + Playwright (Python) + httpx + websockets, executed deterministically; LLM agents only generate, repair, and triage tests.**

### 1.1 Why this stack

| Concern | Choice | Token impact |
|---|---|---|
| Test runner | `pytest` | Zero per re-run |
| Browser automation | `playwright` (Python bindings) | Zero per re-run |
| HTTP API | `httpx` (async) | Zero per re-run |
| WebSocket | `websockets` | Zero per re-run |
| Runtime | Existing repo `.venv` (Python 3.14) | No new toolchain |
| Reporting | `pytest-html`, `pytest-junitxml` | Zero |

A single language (Python) for the server **and** the SQA harness eliminates a second toolchain, reuses the existing venv, and lets the SQA agent reuse server fixtures (`reset_and_seed.py`, OpenAPI client) with no extra dependencies. Playwright Python is API-equivalent to Playwright TS for browser tests, and pytest fixtures provide cheap test isolation.

### 1.2 Token-cost discipline

The dominant cost driver is **how often the LLM is invoked**, not stack choice. The architecture enforces:

1. **Write once, run forever.** An agent emits a Python test file from a markdown plan + OpenAPI spec. The test then runs deterministically forever via `pytest`. No agent invocation per run.
2. **Tiered models.** Cheap model (e.g. small reasoning model) for routine triage and heartbeat updates; capable model only invoked when a test fails and source-of-failure analysis is required (rare path).
3. **No source-tree slurping.** Agents read `docs/`, `SQA/plans/*.md`, and `/api/v1/openapi.json` — *not* the implementation code. The agent prompt enforces this. This caps prompt size at ~20 KB regardless of MES growth.
4. **Module sharding.** Each test module (§2) is generated and triaged independently so failures touch only one module's context, not the whole repo.
5. **Cached context.** A static `SQA/context_pack.md` (route maps, IDs, fixture paths) is regenerated only when `PROJECT_STATE.json` changes, then reused across many runs.

**Rejected alternatives:**

- *Cypress / Playwright TS:* would require a Node toolchain and JS SDK clients, doubling the harness surface. No upside vs. Python.
- *LLM-driven browsing per test (browser-use, OpenAdapt, etc.):* every assertion costs tokens. Suitable for exploratory testing only — see §2.3.
- *Postman/Newman:* not extensible enough for WebSocket and ISA-95 stateful flows.

---

## 2. Test Decomposition — Functional Modules

Tests are organised one folder per **SQA module ID** (mirroring the existing module-ID convention in `PROJECT_STATE.json`). Each module is small enough for a single agent invocation and produces an independent pytest test suite plus its own GitHub issue label.

### 2.1 Module catalog

| Module ID | Scope | Surfaces | Independence |
|---|---|---|---|
| **SQA-DB** | Alembic migrations up/down, seed reproducibility, schema sanity | DB only | Standalone |
| **SQA-API** | REST contract conformance against OpenAPI spec, auth, pagination, error shapes | Server :8082 | Standalone |
| **SQA-WS** | WebSocket topic catalogue (`wip.*`, `dispatch.*`, `equipment.state.*`, `data.*`, `quality.*`) | Server :8082 | Standalone |
| **SQA-PLUGINS** | Plugin install/enable/disable lifecycle, parameter validation | Server + CLI | Standalone |
| **SQA-DT** | DT-CLIENT screens, CRUD pages, navigation, About dialog | DT-CLIENT :5173 | Needs server |
| **SQA-RT** | RT-CLIENT scan, active WIP, dispatch, events, About dialog | RT-CLIENT :5176 | Needs server + seeded data |
| **SQA-ERP** | ERP-Simulator inbound (orders, materials) and outbound (completion, consumption, scrap, labor, downtime, quality, confirmations) | ERP-Sim :5174 | Needs server + plugin |
| **SQA-EQ** | Equipment Simulator state reporting, OEE, auto-simulator | EQ-Sim :5175 | Needs server |
| **SQA-DISPATCH** | Dispatch engine: dual-equipment dispatch, manual disposition, capacity rules | Server + RT-CLIENT | Needs seed |
| **SQA-GENEALOGY** | Forward/backward genealogy, lot/unit consumption tracing, shift-context columns | Server + DT-CLIENT | Needs E2E run output |
| **SQA-PERF** | Performance / OEE rollups | Server + DT-CLIENT | Needs E2E run output |
| **SQA-WORK-SCHED** | Work schedules, shift instances, timezone correctness | Server | Standalone |
| **SQA-E2E-SMT** | Full Electronics/SMT walk-through (existing `E2E_TEST_PLAN.md`) | All 5 surfaces | Owns its seed |
| **SQA-E2E-CPG** | Full CPG walk-through | All 5 surfaces | Owns its seed |
| **SQA-SMOKE** | 60-second post-deploy smoke (server up, each client serves index, login, one CRUD, one WS event) | All | Cheapest gate |

### 2.2 Test layers within each module

Each module folder has up to three layers, ordered cheapest first so an agent can skip the expensive layers on a clean lower layer:

1. **Contract tests** — pure HTTP/WS, validate OpenAPI conformance, invariants. Fast, no browser.
2. **Component tests** — Playwright against a single page/route. Mock the network where helpful.
3. **Scenario tests** — multi-step E2E flows that drive several surfaces.

### 2.3 Optional exploratory layer

A separate `SQA/exploratory/` track uses an LLM-driven browser (Playwright + an agent) to do *unscripted* visual regression on each release candidate. **Off by default** because it spends tokens per click. Triggered manually before a release tag.

### 2.4 Mapping to existing assets

- `SQA/E2E_TEST_PLAN.md` becomes the source plan for `SQA-E2E-SMT`.
- `SQA/SKILL_QA_ENGINEER.md` is generalised into `SQA/agents/runner_agent.md` plus per-module skills.
- Existing `SQA/playwright.config.ts` is replaced by `pytest.ini` + `conftest.py` (Python harness).

---

## 3. Same Workspace vs. Separate SQA Environment

**Recommendation: Same VS Code workspace, separate top-level folder (`SQA/`, already exists). A separate process / venv layer is only introduced for release-candidate certification.**

### 3.1 Same-workspace benefits (chosen)

- Reuses the existing `.venv`, `reset_and_seed.py`, OpenAPI generator, and seed data — no duplication.
- The agent can write tests *and* run them in one session without context-switching IDEs.
- Failure triage can read `server/logs/mes_server.log` and the source if a bug is suspected (controlled — see §3.3).

### 3.2 Risk: implementation bias

If the SQA agent reads server source while authoring tests, it will encode bugs as "expected behaviour".

**Mitigation, enforced by the agent skill prompt:**

- **Authoring phase** restricts read access to `docs/`, `SQA/plans/`, `clients/*/src/types/` (TypeScript types only, no logic), and `/api/v1/openapi.json` served by a running server.
- **Triage phase** (only after a confirmed failure) is allowed to read source under `server/src/mes/` and the relevant client to classify the failure as test-bug vs. product-bug.
- The two phases use different agent prompts (`authoring_agent.md`, `triage_agent.md`) and different file-read allowlists in the agent runner.

### 3.3 When to use a separate environment

A *physically* separate environment (a clean Windows VM or container) is used **only** for the release-candidate gate (§4.2). For day-to-day development, in-workspace is fine.

---

## 4. Code Source — Working Tree vs. Release Candidate

**Recommendation: Two modes.**

### 4.1 Mode A — Development (default)

Tests run against the working tree in the current workspace. Used:

- after every non-trivial commit by the developer agent,
- on demand via `SQA/scripts/run_module.ps1 <MODULE-ID>`,
- on a watcher (optional) that triggers SQA-SMOKE on file save.

Stack started in-process by `SQA/scripts/start_stack.ps1` (server + 4 clients in background terminals), torn down by `stop_stack.ps1`. Database is reset to a known seed state per run via `reset_and_seed.py`.

### 4.2 Mode B — Release-candidate certification

Triggered when a tag like `v1.0.0-rc1` is pushed. The certification script:

1. `gh repo clone point85/mes-ai SQA-RC/<tag>` into a sibling folder.
2. `git checkout <tag>` in the clone.
3. Creates a fresh venv, `pip install -e ".[dev]"`, installs Playwright browsers.
4. Brings the database to a clean state on a separate Postgres database (`mes_ai_rc`), runs `alembic upgrade head` from the tag, runs `reset_and_seed.py`.
5. Starts the stack on alternate ports (`+10000` offset) so it can co-exist with dev.
6. Runs **all** SQA modules in dependency order (DB → API → WS → DT/RT/ERP/EQ → Dispatch → Genealogy → Perf → E2E).
7. Emits a signed `SQA/reports/release/<tag>/REPORT.md` + `report.json` with the pass matrix.
8. Tears down the stack and (on green) tags the commit `<tag>+sqa-passed` via `gh` if explicitly authorised.

This is the only mode that truly certifies "release-quality" — it eliminates working-tree drift, IDE state, and uncommitted files.

### 4.3 Database isolation

Both modes use a dedicated database name (`mes_ai_s95` for dev, `mes_ai_rc` for RC) and never touch the developer's primary database without a `reset_and_seed.py` step the user can audit.

---

## 5. Progress Monitoring

The agent operates autonomously for many minutes per module. Monitoring uses three layers, in order of granularity:

### 5.1 Live status — `SQA/status.json`

Machine-readable, written every action by the agent and by each pytest run via a small plugin. Schema:

```json
{
  "run_id": "2026-05-03T18:42:11Z-7f3a",
  "started_at": "2026-05-03T18:42:11Z",
  "updated_at": "2026-05-03T18:43:05Z",
  "mes_version": "1.0.0",
  "mode": "dev",
  "current_module": "SQA-RT",
  "current_test": "test_release_order_creates_lot",
  "stack": { "server": "up", "dt": "up", "rt": "up", "erp": "up", "eq": "up" },
  "modules": {
    "SQA-DB":  { "status": "passed",  "duration_s": 6.1,  "passed": 8,  "failed": 0 },
    "SQA-API": { "status": "passed",  "duration_s": 22.3, "passed": 47, "failed": 0 },
    "SQA-RT":  { "status": "running", "passed": 3,  "failed": 0 }
  },
  "totals": { "passed": 58, "failed": 0, "skipped": 1 }
}
```

### 5.2 Heartbeat — `SQA/HEARTBEAT.md`

Human-readable, single page, overwritten on each agent action. Shows the last 20 events, the currently running test, and a link to the latest report. The existing file at `SQA/HEARTBEAT.md` is repurposed.

### 5.3 Reports — `SQA/reports/<run_id>/`

Per-run folder containing `report.html` (pytest-html), `junit.xml` (CI-consumable), `screenshots/`, `traces/`, `mes_server.log` snapshot, and `summary.md` written by the triage agent.

### 5.4 Issues

On any confirmed product-bug, the triage agent calls `gh issue create` with:

- title prefix `[SQA-<MODULE-ID>]`,
- body containing failure assertion, screenshot link, server log excerpt, and a minimal repro path,
- labels `qa`, `bug`, and the module ID.

### 5.5 Optional dashboard

An optional `/sqa/status` route in the MES server can render `SQA/status.json` as a small HTML dashboard. Not required for v1.0; documented for future work.

---

## 6. Folder / Directory Structure & Templates

```
SQA/
├── README.md                         # Quick-start (run a module, run all, certify release)
├── SQA_TESTING.md                    # This design doc
├── HEARTBEAT.md                      # Live agent heartbeat (overwritten)
├── status.json                       # Live machine-readable status
├── pyproject.toml                    # SQA harness deps (pinned)
├── pytest.ini                        # markers (smoke, e2e, slow), addopts, junit/html
├── conftest.py                       # Root fixtures: stack URLs, db reset, api/ws clients
│
├── agents/                           # Agent skill / prompt files
│   ├── runner_agent.md               # Orchestrator: picks a module, calls authoring/triage
│   ├── authoring_agent.md            # Generates tests from plans + OpenAPI ONLY
│   ├── triage_agent.md               # Diagnoses failures; allowed to read source
│   └── skills/
│       ├── SQA-API.skill.md
│       ├── SQA-RT.skill.md
│       └── ...                       # one per module
│
├── plans/                            # Markdown test plans per module (agent-readable)
│   ├── SQA-API.md
│   ├── SQA-DT.md
│   ├── SQA-RT.md
│   ├── SQA-ERP.md
│   ├── SQA-EQ.md
│   ├── SQA-DISPATCH.md
│   ├── SQA-GENEALOGY.md
│   ├── SQA-PERF.md
│   ├── SQA-WORK-SCHED.md
│   ├── SQA-PLUGINS.md
│   ├── SQA-WS.md
│   ├── SQA-DB.md
│   ├── SQA-SMOKE.md
│   ├── SQA-E2E-SMT.md                # migrated from existing E2E_TEST_PLAN.md
│   └── SQA-E2E-CPG.md
│
├── modules/                          # Generated tests, one folder per module ID
│   ├── SQA-API/
│   │   ├── README.md                 # What this module covers + module-IDs
│   │   ├── conftest.py               # Module-local fixtures
│   │   ├── test_contract_uom.py
│   │   ├── test_contract_sites.py
│   │   └── ...
│   ├── SQA-RT/
│   ├── SQA-E2E-SMT/
│   └── ...
│
├── fixtures/                         # Shared, deterministic test data + helpers
│   ├── api_client.py                 # Thin httpx wrapper, auto-auth in MES_AUTH_MODE=none
│   ├── ws_client.py                  # async websockets helper, topic filter
│   ├── ui_helpers.py                 # Playwright login, navigate-to-route, table assertions
│   ├── seed.py                       # Wraps reset_and_seed.py + adds per-test snapshots
│   └── topics.py                     # Canonical event-topic catalogue
│
├── reports/                          # Per-run output
│   ├── latest/                       # Symlink/copy to most recent
│   └── 2026-05-03T18-42-11Z-7f3a/
│       ├── report.html
│       ├── junit.xml
│       ├── summary.md
│       ├── server.log
│       └── screenshots/
│
├── screenshots/                      # Per-test screenshots (already exists)
│
├── context_pack.md                   # Cached context loaded by every agent invocation
│
├── scripts/                          # PowerShell + bash entry points
│   ├── start_stack.ps1               # Start server + 4 clients (background)
│   ├── stop_stack.ps1
│   ├── reset_db.ps1                  # Calls server/scripts/reset_and_seed.py
│   ├── run_module.ps1                # ./run_module.ps1 SQA-RT
│   ├── run_all.ps1                   # Sequential full run, in dep order
│   ├── certify_release.ps1           # Mode B (release-candidate) full pipeline
│   └── watch_smoke.ps1               # Optional: file-watcher → SQA-SMOKE
│
└── templates/                        # Boilerplate the authoring agent copies
    ├── module_README.md.tmpl
    ├── test_contract.py.tmpl         # API test scaffold
    ├── test_component.py.tmpl        # Playwright single-page scaffold
    ├── test_scenario.py.tmpl         # Multi-step E2E scaffold
    └── plan.md.tmpl                  # Plan structure (purpose, preconditions, steps, oracles)
```

### 6.1 Template settings — `pytest.ini` (planned)

```ini
[pytest]
addopts = -ra --strict-markers --html=reports/latest/report.html --self-contained-html --junitxml=reports/latest/junit.xml
testpaths = modules
markers =
    smoke: 60-second post-deploy gate
    api: REST contract layer
    ws: websocket layer
    ui: requires a running browser
    e2e: full multi-surface scenario
    slow: > 30s
    requires_seed: needs reset_and_seed.py to run first
asyncio_mode = auto
```

### 6.2 Template settings — `conftest.py` (planned shape)

Provides session-scoped fixtures that the authoring agent must use rather than reinventing:

- `mes_urls` → dict of `server / dt / rt / erp / eq` URLs (driven by env vars with sensible defaults from `MES AI.txt`).
- `api` → authenticated `httpx.AsyncClient`.
- `ws` → factory for `websockets` connections by topic filter.
- `clean_db` → resets DB and reseeds (function-scoped on `requires_seed` only).
- `browser_context` → Playwright context with viewport from env.

### 6.3 Template settings — plan markdown

Each `plans/<MODULE-ID>.md` follows a fixed structure so the authoring agent can parse it without LLM reasoning:

```
# <MODULE-ID> — <Title>
## Purpose
## Preconditions   (data state, plugins, seeds)
## Surfaces under test
## Test cases
### TC-001 <name>
- Steps:
- Oracles (assertions):
- Negative variants:
## Out of scope
## Source of truth   (which docs/ files define correctness)
```

### 6.4 Template settings — `agents/runner_agent.md` (shape)

Defines the orchestration loop: pick a module → load its plan → call `authoring_agent` if tests are missing or stale → run pytest deterministically → on failure, call `triage_agent` → write status/heartbeat → optionally `gh issue create`.

---

## 7. Implementation Plan (next tasks, *not* executed by this doc)

1. **SQA-BOOT** — Create `pyproject.toml`, `pytest.ini`, `conftest.py`, `fixtures/`, `scripts/start_stack.ps1`/`stop_stack.ps1`/`reset_db.ps1`, `templates/`. Pin Playwright + browsers. Smoke-test that `pytest` collects zero tests cleanly.
2. **SQA-AGENTS** — Author `agents/runner_agent.md`, `authoring_agent.md`, `triage_agent.md`, `skills/*.skill.md`. Author `context_pack.md` generator.
3. **SQA-PLANS** — Migrate `E2E_TEST_PLAN.md` into `plans/SQA-E2E-SMT.md`; stub the remaining `plans/*.md` from `docs/ARCHITECTURE.md` and `docs/DICTIONARY.md`.
4. **SQA-SMOKE** — Implement first, smallest module end-to-end: validates the harness itself.
5. **SQA-API** — First substantive module; OpenAPI-driven so it scales as endpoints are added.
6. **SQA-WS / SQA-DB / SQA-PLUGINS** — Standalone modules, low cost.
7. **SQA-DT / SQA-RT / SQA-ERP / SQA-EQ** — Browser modules.
8. **SQA-DISPATCH / SQA-GENEALOGY / SQA-PERF / SQA-WORK-SCHED** — Cross-cutting.
9. **SQA-E2E-SMT / SQA-E2E-CPG** — Reuse output of upstream modules.
10. **SQA-RC** — `scripts/certify_release.ps1` and the `reports/release/<tag>/` flow.

Each numbered item is sized for one agent session.

---

## 8. Open Questions / Decisions to Confirm

The following are sensible defaults; flag any you want changed before SQA-BOOT begins.

1. **Auth mode for tests:** default `MES_AUTH_MODE=none`. Add a separate auth-on smoke later? *(default: yes, deferred)*
2. **Headed vs. headless browser:** default headless in CI, headed locally via `SQA_HEADED=1`. *(default: ok)*
3. **Issue creation:** auto on every confirmed failure, or only on the RC pipeline? *(default: auto in dev too, with `[SQA]` prefix and dedup-by-fingerprint)*
4. **Models:** default cheap model for authoring, capable model for triage; configurable via `SQA_MODEL_AUTHOR` / `SQA_MODEL_TRIAGE` env vars. *(default: ok)*
5. **CI integration:** out of scope for this doc; the pytest harness is CI-ready (JUnit XML) when chosen.

---

## 9. Summary

- **Stack:** pytest + Playwright Python + httpx + websockets, deterministic re-execution, LLMs only for authoring and triage.
- **Decomposition:** ~15 module IDs, each agent-sized, organised by surface and concern; existing `E2E_TEST_PLAN.md` becomes one of them.
- **Environment:** same VS Code workspace; isolated agent prompts prevent implementation bias; release-candidate gate runs in a fresh clone of the tag.
- **Source under test:** working tree for dev; `gh repo clone` + tag checkout for RC certification.
- **Monitoring:** `status.json` (machine), `HEARTBEAT.md` (human), `reports/<run_id>/` (durable), GitHub Issues (action items).
- **Layout:** `SQA/{plans,modules,fixtures,agents,scripts,templates,reports}` with fixed-shape templates so subsequent agent work is mechanical rather than creative.

---

## 10. SQA-DT / TC-UOM-001 example

Worked example of how the agents execute a CRUD-editor test in DT-CLIENT, using the **Unit of Measure** editor as the case. The same pattern applies to every other CRUD page (Sites, Areas, Equipment Classes, Products, Routes, …).

**Key idea:** the agent does *not* drive the browser at run time. The agent writes a Playwright/pytest script *once*; thereafter `pytest` drives a real Chromium against the running DT-CLIENT, and the agent is only re-invoked if the test fails.

### 10.1 One-time authoring (agent invocation, costs tokens)

Inputs the **authoring agent** is allowed to read:

- `SQA/plans/SQA-DT.md` — human-curated test plan (steps + oracles)
- `docs/DICTIONARY.md` — UoM field semantics
- `http://localhost:8082/api/v1/openapi.json` — the UoM REST contract (field names, validation, response shape)
- `clients/design_time/src/types/` — TypeScript types only (no logic)

Inputs it is **forbidden** from reading: `clients/design_time/src/pages/uom/*.tsx`, `server/src/mes/**`. This is what prevents the test from encoding bugs as expected behaviour.

It emits a single file, e.g. `SQA/modules/SQA-DT/test_uom_crud.py`, using the `test_component.py.tmpl` template:

```python
import pytest
from playwright.async_api import expect

@pytest.mark.ui
@pytest.mark.requires_seed
async def test_uom_create_edit_delete(page, mes_urls, api):
    # Arrange — start from a known DB state via the API, not the UI
    code = "SQA_TEST_UOM_001"
    await api.delete(f"/api/v1/uoms/by-code/{code}")  # idempotent cleanup

    # Act — drive the DT-CLIENT
    await page.goto(f"{mes_urls['dt']}/uom")
    await page.get_by_role("button", name="New UoM").click()
    await page.get_by_label("Code").fill(code)
    await page.get_by_label("Name").fill("SQA Test Unit")
    await page.get_by_label("Symbol").fill("sqa")
    await page.get_by_label("Category").select_option("count")
    await page.get_by_role("button", name="Save").click()

    # Assert (UI oracle) — row appears
    row = page.get_by_role("row", name=code)
    await expect(row).to_be_visible()

    # Assert (API oracle) — server actually persisted it
    resp = await api.get(f"/api/v1/uoms/by-code/{code}")
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "SQA Test Unit"

    # Edit
    await row.get_by_role("button", name="Edit").click()
    await page.get_by_label("Name").fill("SQA Test Unit v2")
    await page.get_by_role("button", name="Save").click()
    await expect(page.get_by_role("cell", name="SQA Test Unit v2")).to_be_visible()

    # Delete
    await row.get_by_role("button", name="Delete").click()
    await page.get_by_role("button", name="Confirm").click()
    await expect(row).not_to_be_visible()
    assert (await api.get(f"/api/v1/uoms/by-code/{code}")).status_code == 404
```

Key authoring rules baked into the template:

- **Selectors are role/label-based** (`get_by_role`, `get_by_label`), not CSS classes — the test survives Tailwind and layout refactors and doesn't require source reading.
- **Every UI assertion has a paired API oracle.** The UI alone can lie ("toast says Saved" while the POST 500'd silently). Hitting `/api/v1/uoms/by-code/...` confirms the editor actually persisted the change.
- **Setup/teardown happens via the API**, not the UI — faster and isolates the test from unrelated UI bugs.

### 10.2 Repeat execution (zero tokens)

`SQA/scripts/run_module.ps1 SQA-DT` does:

1. `start_stack.ps1` → server :8082 + DT :5173 in background terminals (skipped if already up).
2. `reset_db.ps1` → `python server/scripts/reset_and_seed.py` (only if the test is marked `requires_seed`).
3. `pytest -m ui modules/SQA-DT -k uom`.
4. `conftest.py` provides:
   - `page` — Playwright page from a session-scoped browser
   - `mes_urls` — dict from env (`SQA_DT_URL=http://localhost:5173` default)
   - `api` — auth'd `httpx.AsyncClient`
5. Pytest writes `reports/<run_id>/{report.html,junit.xml,screenshots/}`.

No LLM in this loop. The test can be re-run unlimited times for the cost of electricity.

### 10.3 On failure (agent invocation, costs tokens — rare)

`pytest` produces:

- failure assertion + traceback,
- automatic Playwright screenshot + trace (`trace: 'on-first-retry'`),
- a snippet of `server/logs/mes_server.log` for the failure window.

The **triage agent** is invoked with that bundle and is now allowed to read source. It classifies:

- **Test bug** (e.g. a button label changed from "New UoM" to "Add UoM") → it patches the test file, re-runs once. Done.
- **Product bug** (e.g. POST returned 200 but no row created) → it calls `gh issue create` with title `[SQA-DT] UoM create returns 200 but does not persist`, attaches screenshot + log excerpt + the failing oracle, and stops.

### 10.4 Why this works for *all* CRUD editors uniformly

Every DT-CLIENT CRUD page has the same shape: list page → "New" button → form dialog → table row → Edit/Delete. So the `test_component.py.tmpl` template parametrises:

- `entity_name` (e.g. `uom`, `site`, `equipment_class`)
- list URL, API base path
- form fields + sample values from OpenAPI

→ One template + the OpenAPI spec lets the authoring agent emit the test for **any** new CRUD editor in one shot, without reading the editor's source.

### 10.5 TL;DR

Agent → writes Playwright/pytest test once → pytest + headless Chromium drive the DT-CLIENT and verify both the UI **and** the REST API → tokens are spent only on first authoring and on the rare triage path.

