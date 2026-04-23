# End-to-End SMT Line Test

A manual walkthrough that exercises the **Electronics / SMT** demo across all four browser clients and the server. Intended for an SQA engineer to run after a build. Each section lists the exact UI actions plus the expected result.

> Automated Playwright coverage lives under `SQA/tests/`. This document is the human-driven complement.

---

## 1. Prerequisites

- PostgreSQL 16+ running on `localhost:5432` with super-user `postgres` / `postgres`.
- Node 20+, Python 3.14, and the repo's Python venv activated.
- A clean database state (the seed does not merge with previous runs). To reset:

  ```powershell
  cd c:\dev\mes_ai\server
  c:\dev\mes_ai\.venv\Scripts\python.exe scripts\reset_and_seed.py
  ```

  This drops `mes_ai`, re-creates it, runs `alembic upgrade head`, seeds built-in UoMs, and seeds **both** the CPG and Electronics demos (ERP + plant sides). When it finishes you should see:

  - `Electronics ERP demo data seeded: {..., 'process_segments': 8, 'transitions': 12, ...}`
  - `Electronics plant demo data seeded: {..., 'equipment': 8, 'equipment_classes': 7, ...}`

## 2. Start the stack

Open five terminals from the repo root:

| Terminal | Command | URL |
|---|---|---|
| Server | `cd server; c:\dev\mes_ai\.venv\Scripts\python.exe -m uvicorn mes.main:app --reload --port 8082` | http://localhost:8082 |
| DT-CLIENT | `cd clients/design_time; npm run dev` | http://localhost:5173 |
| ERP Simulator | `cd clients/erp_simulator; npm run dev` | http://localhost:5174 |
| Equipment Simulator | `cd clients/equipment_simulator; npm run dev` | http://localhost:5175 |
| RT-CLIENT | `cd clients/run_time; npm run dev` | http://localhost:5176 |

All Vite dev servers proxy `/api` → `http://localhost:8082`. Confirm `GET http://localhost:8082/health` returns `{"status":"ok"}` before proceeding.

---

## 3. (Optional) Re-seed via the UI instead of the script

If you used `reset_and_seed.py` in step 1, skip this section — the data is already loaded.

Otherwise, seed interactively:

1. **ERP Simulator → Dashboard** → click **Seed Electronics Demo**. Expect a summary that lists `process_segments: 8`, `transitions: 12`, `bom_items: 8`, `dispositions: 8`.
2. **DT-CLIENT → Dashboard** → click **Seed Electronics Demo**. Expect a summary that lists `equipment: 8`, `equipment_classes: 7`, `work_cells: 7`, `equipment_capabilities: 8`.

> Run the ERP seed first — the plant seed links equipment to segments created by the ERP seed.

---

## 4. Verify the configuration in DT-CLIENT (http://localhost:5173)

### 4.1 Physical Model

Navigate to **Sites → Apex Electronics → PCBA Area → LINE-SMT-01** and confirm:

- 7 work cells: `WC-PASTE`, `WC-PLACE`, `WC-REFLOW`, `WC-AOI`, `WC-THT`, `WC-TEST`, `WC-REWORK`.
- 8 equipment items across those cells — including **two** pick-and-place machines at `WC-PLACE`: `PNP-800A` and `PNP-800B`.

### 4.2 Equipment Classes

Navigate to **Equipment Classes**. Confirm all seven: `PRINTER`, `PLACEMENT`, `OVEN`, `INSPECTION`, `WAVE_SOLDER`, `TESTER`, `MANUAL`. Open **PLACEMENT** and confirm its members are `PNP-800A` **and** `PNP-800B` — this is what makes dual-equipment dispatch possible downstream.

### 4.3 Routes

Navigate to **Routes → SMT Assembly Line (v1.0)**. Confirm 8 process segments in sequence order:

| Seq | Name | Step type | Work cell | Cycle time (s) |
|---|---|---|---|---|
| 10 | Solder Paste Application | production | WC-PASTE | 30 |
| 20 | SMD Placement | production | WC-PLACE | 45 |
| 30 | Reflow Soldering | production | WC-REFLOW | 180 |
| 40 | Automated Optical Inspection | inspection | WC-AOI | 20 |
| 50 | Through-Hole & Conformal Coat | production | WC-THT | 120 |
| 60 | Functional Test | inspection | WC-TEST | 60 |
| 70 | Rework Station | rework | WC-REWORK | 300 |
| 80 | MRB Review | mrb | WC-REWORK | 600 |

The graph should include the rework loop: `AOI → Rework (on_fail)`, `Functional Test → Rework (on_fail)`, `Rework → AOI (always)` plus escalation edges `AOI → MRB` and `Functional Test → MRB` on `on_rework`.

### 4.4 Products & BOM

Navigate to **Products → FG-ECB-100 (Electronic Controller Board v1)**. Confirm a BOM with **8 items**: `RM-PCB-BLANK`, `RM-SMD-KIT`, `RM-THRU-KIT`, `RM-SOLDER-PST` (5 g), `RM-FLUX` (2 mL), `RM-CONFORMAL` (3 mL), `SF-POP-PCB`, `PKG-ESD-BAG`. Each BOM item mapped to a step should show its `step_sequence`.

### 4.5 Dispositions

Navigate to **Dispositions**. Confirm 8 codes exist: `E-START`, `E-PASS-SMD`, `E-PASS-REFL`, `E-PASS-AOI`, `E-AOI-PASS`, `E-TH-PASS`, `E-REWORK` (category `route`), `E-ESCALATE` (category `hold`).

---

## 5. Create and release a production order (ERP Simulator @ :5174)

1. **Orders → New Order**: product `FG-ECB-100`, quantity `5`, priority `normal`. Save.
2. The new row should appear with status `created`.
3. Click **Release**. Row should flip to `released`; server emits `operations.request.released`.
4. Switch to **RT-CLIENT → Events** (http://localhost:5176) and confirm the release event arrives on the WebSocket feed.

---

## 6. Process WIP through the SMT route (RT-CLIENT @ :5176)

Each of the 5 units (`SN-…-00001` … `00005`) should be walked through the graph. For at least one unit, divert through the rework loop (`AOI → Rework → AOI → Pass`) to exercise the full topology.

For each unit:

1. **Scan** page → enter the unit serial (or pick it from **Orders → unit list**).
2. **Active WIP** should now show the unit at sequence 10 (Solder Paste).
3. In the **Step Processing** panel:
   - Equipment selector defaults to **Auto (dispatch algorithm)**. On the SMD Placement step (seq 20) the selector's drop-down must list **both `PNP-800A` and `PNP-800B`** (this is the dual-equipment dispatch check).
   - Click **Start** → equipment transitions to busy. Verify in **DT-CLIENT → Performance** or **Equipment Simulator**.
   - Click **Complete** → pick the disposition wired to the outgoing `on_pass` / `always` edge. Typical happy-path sequence:
     - Solder Paste → disposition `E-START`
     - SMD Placement → `E-PASS-SMD`
     - Reflow Soldering → `E-PASS-REFL`
     - AOI → `E-PASS-AOI` (happy path) **or** select an `on_fail` disposition to route to Rework
     - Through-Hole & Conformal Coat → `E-AOI-PASS`
     - Functional Test → `E-TH-PASS`
4. After the last step, the unit transitions to `complete` and BOM quantities (`RM-PCB-BLANK`, `RM-SMD-KIT`, `RM-SOLDER-PST`, etc.) are consumed from inventory.

While processing, keep an eye on:

- **RT-CLIENT → Active WIP** — step advancement.
- **RT-CLIENT → Events** — topics `wip.unit.*`, `dispatch.*`, `data.*`, `equipment.state.*`, `quality.*` should fire.
- **DT-CLIENT → Inventory** — consumption rows for each lot.

---

## 7. Verify completion flows back to ERP

1. When all 5 units reach `complete`, the order should auto-transition to `completed`. Otherwise click **Complete** on the order row.
2. In **ERP Simulator → Confirmations** (and the **Completion / Consumption / Scrap** tabs), confirm:
   - Good quantity = 5 (minus any units you intentionally scrapped/rejected).
   - Material consumption matches `BOM × 5` for each raw.
3. **Orders**: order status is `completed`, `quantity_completed = 5`.

---

## 8. Spot-check analytics in DT-CLIENT

- **Performance / OEE**: each SMT work cell shows availability / performance / quality for the run. Dual PNP cell should show both `PNP-800A` and `PNP-800B` individually.
- **Genealogy**: look up one serial (`SN-…-00001`). The tree should show consumed raw materials (lot numbers), the equipment that processed each step, timestamps, and the quality-test results.
- **Dispatch** (DT-CLIENT): any items that were queued during the run returned to zero queue depth.

---

## 9. Pass criteria

- All 5 units completed on the correct disposition path, including at least one transit through the rework loop.
- BOM consumption, scrap (if any), and completion rows delivered to the ERP Simulator with matching quantities.
- No ERROR-level entries in `server/logs/mes_server.log` for the run window.
- RT-CLIENT event stream shows `operations.request.*`, `wip.unit.*`, `dispatch.*`, `data.*`, `equipment.state.*`, and `quality.*` topics end-to-end.
- Genealogy and OEE reflect the run.
- Dual-equipment dispatch: during SMD Placement, both `PNP-800A` and `PNP-800B` were selectable, and the dispatch engine chose between them per strategy.

---

## 10. Optional automated variant

Replace the manual **Start** / **Complete** clicks in §6 with the **Equipment Simulator** client (http://localhost:5175). It drives equipment state and counters via PackML (OPC-UA) or MQTT plugins, producing the same event stream without human interaction.
# End-to-End SMT Line Test

Exercises the Electronics (SMT) demo across DT-CLIENT (design-time config), ERP Simulator (order/completion), and RT-CLIENT (shop-floor execution).

## 1. Start the stack

Open four terminals from the repo root and run:

| Terminal | Command | URL |
|---|---|---|
| Server | `cd server; uvicorn mes.main:app --reload --port 8000` | http://localhost:8000 |
| DT-CLIENT | `cd clients/design_time; npm run dev` | http://localhost:5173 |
| ERP Simulator | `cd clients/erp_simulator; npm run dev` | http://localhost:5174 |
| RT-CLIENT | `cd clients/run_time; npm run dev` | http://localhost:5175 |

Point the server at the ISA-95 DB: `MES_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mes_ai_s95` and run `alembic upgrade head` plus `python scripts/seed_uom.py` once.

## 2. Seed the SMT demo data

1. In **DT-CLIENT → Dashboard**, click **Seed Electronics Plant** → creates site, PCBA area, `LINE-SMT-01`, 7 work cells, 8 equipment (incl. dual `PNP-800A/B`), and assigns each to its equipment class.
2. In **ERP Simulator → Dashboard**, click **Seed Electronics ERP** → creates materials, `FG-ECB-100` product, BOM, `SMT Assembly Line` route (5 process segments: Solder Paste → SMD Placement → Reflow → AOI → Through-Hole), dispositions, data definitions, and quality tests.

## 3. Verify the configuration in DT-CLIENT

- **Sites → PCBA Area → LINE-SMT-01 → Work Cells**: all 7 present.
- **Equipment Classes**: `PRINTER`, `PLACEMENT`, `OVEN`, `INSPECTION`, `WAVE_SOLDER`, `TESTER`, `MANUAL` each have members.
- **Products → FG-ECB-100**: BOM has 8 lines; route has 5 process segments with expected cycle times and dispositions.
- **Dispatch**: confirm `PNP-800A` and `PNP-800B` both appear under the SMD Placement segment (dual-equipment dispatch).

## 4. Create and release a production order (ERP Simulator)

1. **Orders → New**: product `FG-ECB-100`, quantity `5`, priority `normal` → Save.
2. Click **Release**. The row should flip to `released` and emit `operations.request.released` on the event bus.
3. In **RT-CLIENT → Events** tab, confirm the release event arrives via WebSocket.

## 5. Process WIP through the SMT route (RT-CLIENT)

For each of the 5 serialized units (`SN-…-00001` … `00005`):

1. **Scan** page → enter the unit serial (or pick from **Orders → unit list**).
2. **Active WIP** shows the unit at sequence 10 (Solder Paste). Click **Start** → equipment state transitions to busy; verify on DT-CLIENT **Performance** / Equipment Sim.
3. Click **Complete** and pick disposition `E-PASS-SMD` → unit advances to SMD Placement. The dispatch engine selects `PNP-800A` or `PNP-800B` per strategy.
4. Repeat Start/Complete for **Reflow** (`E-PASS-REFL`), **AOI** (`E-AOI-PASS` — or `E-REWORK` on one unit to exercise the rework loop), and **Through-Hole & Conformal Coat** (`E-TH-PASS`).
5. After the final step, the unit completes and consumes BOM quantities (`RM-PCB-BLANK`, `RM-SMD-KIT`, `RM-SOLDER-PST`, etc.) from inventory.

Watch **RT-CLIENT → Active WIP**, **Inventory**, and **Events** to confirm `wip.unit.*`, `dispatch.*`, `data.*`, and `equipment.state.*` topics fire as expected.

## 6. Verify completion flows back to ERP

1. When all 5 units finish, the order auto-completes (or click **Complete** on the order row).
2. In **ERP Simulator → Confirmations** (and **Completion** / **Consumption** / **Scrap** tabs): verify rows for good qty 5, scrap 0 (or 1 if you sent one unit to rework/scrap), and material consumption matching BOM × 5.
3. In **ERP Simulator → Orders**: status is `completed`, `quantity_completed = 5`.

## 7. Spot-check analytics in DT-CLIENT

- **Performance**: OEE for each SMT work cell shows availability/performance/quality for the run.
- **Genealogy**: look up one serial → tree shows consumed raw materials, the equipment that processed each step, timestamps, and quality test results.
- **Dispatch**: queue depths for `PNP-800A/B` returned to zero.

## 8. Pass criteria

- 5 units completed with correct disposition path (including any rework loop you triggered).
- BOM consumption, scrap, and completion rows delivered to ERP Simulator with matching quantities.
- No errors in server log; event stream in RT-CLIENT shows expected topics end-to-end.
- Genealogy and OEE reflect the run.

Optionally, replace manual Start/Complete clicks with the **Equipment Simulator** client to drive state/counter changes via PackML OPC-UA or MQTT plugins for a fully automated variant of the same flow.