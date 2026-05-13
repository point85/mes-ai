# SQA-DT — DT-CLIENT Design-Time UI Tests

## Purpose
Validate every CRUD editor in the DT-CLIENT against the REST API contract and the documented
requirements in `docs/ARCHITECTURE.md` and `docs/DICTIONARY.md`.
Tests are authored once from this plan + the live OpenAPI spec; thereafter `pytest` runs them
deterministically at zero token cost.

## Preconditions
- MES server running on `http://localhost:8081` with `MES_AUTH_MODE=none`.
- DT-CLIENT (Vite dev server) running on `http://localhost:5177`.
- Database seeded (or at minimum: no conflicting rows for the test symbols used below).
- Python venv active with `pytest`, `playwright`, `httpx` installed.

## Surfaces under test
- DT-CLIENT route `/uom` → `UoMListPage` component

## Source of truth
- `docs/ARCHITECTURE.md` §UoM / §Unit of Measure
- `docs/DICTIONARY.md` — UoM field semantics
- `http://localhost:8081/api/v1/openapi.json` — REST contract
- `clients/design_time/src/types/uom.ts` — TypeScript field names (types only, no logic)

---

## Test cases

### TC-UOM-001 — Create a scalar unit of measure
- **Steps:**
  1. Navigate to `http://localhost:5177/uom`.
  2. Assert page heading "Units of Measure" is visible.
  3. Click the "New Unit" button.
  4. Fill in Symbol = `SQA_kg2`, Name = `SQA Test Kilogram`, Type = `mass`, Class = `scalar`,
     Multiplier = `1.0`, Offset = `0.0`.
  5. Submit the form (click Save / OK button).
  6. Assert the new row appears in the table with symbol `SQA_kg2`.
  7. Assert via API: `GET /api/v1/uom/symbol/SQA_kg2` returns `200` and `data.symbol == "SQA_kg2"`.
- **Oracles:**
  - Table row visible with correct symbol, name, type badge "Mass", class badge "scalar".
  - API GET by symbol returns `200` with matching fields.
- **Negative variants:**
  - Submit with empty Symbol → form validation error, no API call.
  - Submit duplicate symbol → server returns `409`, toast/error shown, row not duplicated.

### TC-UOM-002 — Edit a scalar unit of measure
- **Steps:**
  1. Ensure `SQA_kg2` exists (created by TC-UOM-001 or via API POST in setup).
  2. Navigate to `http://localhost:5177/uom`.
  3. Find the row for `SQA_kg2` and click its pencil (Edit) icon.
  4. Change Name to `SQA Test Kilogram Edited`.
  5. Submit the form.
  6. Assert the table row updates to the new name.
  7. Assert via API: `GET /api/v1/uom/symbol/SQA_kg2` returns `data.name == "SQA Test Kilogram Edited"`.
- **Oracles:**
  - Row name updated in table without page reload.
  - API confirms updated name.
- **Negative variants:**
  - Clear Symbol field and submit → validation error.

### TC-UOM-003 — Delete a non-built-in unit of measure
- **Steps:**
  1. Ensure `SQA_kg2` exists.
  2. Navigate to `http://localhost:5177/uom`.
  3. Find the row for `SQA_kg2` and click its trash (Delete) icon.
  4. Confirm the browser `confirm()` dialog.
  5. Assert the row is removed from the table.
  6. Assert via API: `GET /api/v1/uom/symbol/SQA_kg2` returns `404`.
- **Oracles:**
  - Row disappears from table after confirm.
  - API returns `404` (soft-delete makes unit inactive).
- **Negative variants:**
  - Attempt delete on a built-in unit → trash icon is disabled, click has no effect.

### TC-UOM-004 — Create a quotient composite unit (e.g. m/s)
- **Steps:**
  1. Navigate to `http://localhost:5177/uom`.
  2. Click "New Unit". Set Symbol = `SQA_mps`, Name = `SQA Metres per Second`,
     Type = `length`, Class = `quotient`.
  3. Select left component = `m`, right component = `s`.
  4. Submit the form.
  5. Assert row appears with formula `m ÷ s`.
  6. Assert via API: `GET /api/v1/uom/symbol/SQA_mps` returns `200`,
     `data.uom_class == "quotient"`, `data.left_uom_symbol == "m"`, `data.right_uom_symbol == "s"`.
- **Oracles:**
  - Formula column shows `m ÷ s`.
  - API confirms class and component symbols.
- **Cleanup:** DELETE `SQA_mps` via API after assertion.

### TC-UOM-005 — Built-in unit cannot be deleted via UI
- **Steps:**
  1. Navigate to `http://localhost:5177/uom`.
  2. Locate a built-in unit row (Built-in column shows ✓, e.g. `kg`).
  3. Assert the trash icon button has attribute `disabled`.
  4. (Optional) Assert clicking it produces no confirm dialog.
- **Oracles:**
  - Delete button disabled for all built-in rows.

### TC-UOM-006 — Type filter narrows table
- **Steps:**
  1. Navigate to `http://localhost:5177/uom`.
  2. Select type filter = `mass`.
  3. Assert all visible rows have Type badge "Mass".
  4. Select type filter = "" (all).
  5. Assert rows from multiple types are visible.
- **Oracles:**
  - Only mass-type rows visible when filter active.
  - All rows visible when filter cleared.

---

## Out of scope
- Conversion panel (UoMConvertPanel) — separate TC set.
- Power-class composite UoMs — deferred to TC-UOM-007+.
- Pagination behaviour — deferred.
- Auth-on mode — deferred (using `MES_AUTH_MODE=none`).

---

## Cleanup note
All test symbols are prefixed `SQA_` to avoid collisions with seeded data.
The `conftest.py` `uom_cleanup` fixture deletes all `SQA_*` symbols via the API after each test.
