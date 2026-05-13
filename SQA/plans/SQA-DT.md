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
- DT-CLIENT route `/work-schedules` → `WorkScheduleListPage` component
- DT-CLIENT route `/work-schedules/:scheduleId` → `WorkScheduleDetailPage` component (`Shifts` tab)

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

---

## Work Schedule test cases

### TC-WS-001 — Create a work schedule
- **Steps:**
  1. Navigate to `http://localhost:5177/work-schedules`.
  2. Click `New Schedule`.
  3. Fill Name = `SQA Work Schedule Alpha`, Description = `SQA alpha schedule`.
  4. Save.
  5. Assert row appears in the list.
  6. Assert via API: `GET /api/v1/work-schedules` contains the schedule and `GET /api/v1/work-schedules/{id}` returns matching `name` / `description`.
- **Oracles:**
  - Schedule appears in DT-CLIENT list.
  - API detail shows empty `shifts`, `rotations`, `teams`, and `non_working_periods` arrays on creation.

### TC-WS-002 — Edit a work schedule
- **Steps:**
  1. Seed `SQA Work Schedule Alpha` via API.
  2. Navigate to `http://localhost:5177/work-schedules`.
  3. Click Edit.
  4. Change Name to `SQA Work Schedule Beta`, Description to `SQA beta schedule`.
  5. Save.
  6. Assert updated row appears.
  7. Assert via API detail that `name` / `description` match the update.

### TC-WS-003 — Delete a work schedule
- **Steps:**
  1. Seed `SQA Work Schedule Gamma` via API.
  2. Navigate to `http://localhost:5177/work-schedules`.
  3. Click Delete and accept the confirm dialog.
  4. Assert row disappears.
  5. Assert via API detail `GET /api/v1/work-schedules/{id}` returns `404`.

### TC-WS-004 — Open work schedule detail page
- **Steps:**
  1. Seed `SQA Work Schedule Alpha` via API.
  2. Navigate to `http://localhost:5177/work-schedules`.
  3. Click `Open detail`.
  4. Assert the detail page loads and the `Shifts`, `Rotations`, `Teams`, and `Non-Working Periods` tabs render.

### TC-WS-SHIFT-001 — Create a shift
- **Steps:**
  1. Seed `SQA Shift Schedule` via API.
  2. Navigate to `http://localhost:5177/work-schedules/{id}`.
  3. In `Shifts`, click `New Shift`.
  4. Fill Name = `SQA Day Shift`, Description = `SQA primary shift`, Start Time = `06:00`, Hours = `8`, Minutes = `30`.
  5. Save.
  6. Assert the shift row shows `06:00` and `8h 30m`.
  7. Assert via API detail that the shift was created with `start_time == 06:00:00` and `duration_seconds == 30600`.

### TC-WS-SHIFT-002 — Edit a shift
- **Steps:**
  1. Seed `SQA Shift Schedule` and `SQA Day Shift` via API.
  2. Navigate to the schedule detail page.
  3. Click Edit on the shift row.
  4. Change Name to `SQA Evening Shift`, Description to `SQA updated shift`, Start Time to `14:15`, Hours to `9`, Minutes to `0`.
  5. Save.
  6. Assert the row updates and the API detail reflects the edited values.

### TC-WS-SHIFT-003 — Delete a shift
- **Steps:**
  1. Seed `SQA Shift Schedule` and `SQA Day Shift` via API.
  2. Navigate to the schedule detail page.
  3. Click Delete on the shift row and accept the confirm dialog.
  4. Assert the shift row disappears.
  5. Assert via API detail that the shift is no longer present.

### TC-WS-SHIFT-004 — Add and remove a break
- **Steps:**
  1. Seed `SQA Shift Schedule` and `SQA Day Shift` via API.
  2. Navigate to the schedule detail page.
  3. Expand the shift card.
  4. Click `Add Break`.
  5. Fill Name = `SQA Lunch Break`, Start Time = `10:30`, Duration = `30`.
  6. Save.
  7. Assert the break row appears in the expanded shift card.
  8. Assert via API detail that the break exists with `start_time == 10:30:00` and `duration_seconds == 1800`.
  9. Click the break delete icon.
  10. Assert the break row disappears and the API detail no longer includes it.

### TC-WS-ROT-001 — Create a rotation
- **Steps:**
  1. Seed `SQA Rotation Schedule` via API.
  2. Navigate to `http://localhost:5177/work-schedules/{id}` and open `Rotations`.
  3. Click `New Rotation`.
  4. Fill Name = `SQA Rotation A`, Description = `SQA first rotation`.
  5. Save.
  6. Assert the rotation card appears and initially shows `0 days`.
  7. Assert via API detail that the rotation exists with no segments.

### TC-WS-ROT-002 — Edit a rotation
- **Steps:**
  1. Seed `SQA Rotation Schedule` and `SQA Rotation A` via API.
  2. Navigate to the `Rotations` tab.
  3. Click Edit on the rotation card.
  4. Change Name to `SQA Rotation B`, Description to `SQA updated rotation`.
  5. Save.
  6. Assert the rotation card updates and API detail reflects the change.

### TC-WS-ROT-003 — Delete a rotation
- **Steps:**
  1. Seed `SQA Rotation Schedule` and `SQA Rotation A` via API.
  2. Navigate to the `Rotations` tab.
  3. Click Delete and accept the confirm dialog.
  4. Assert the rotation card disappears.
  5. Assert via API detail that the rotation is no longer present.

### TC-WS-ROT-004 — Add and remove a rotation segment
- **Steps:**
  1. Seed `SQA Rotation Schedule`, one shift, and `SQA Rotation A` via API.
  2. Navigate to the `Rotations` tab.
  3. Expand the rotation card.
  4. Click `Add Segment`.
  5. Choose the shift and set `Days On = 5`, `Days Off = 2`, `Sequence = 1`.
  6. Save.
  7. Assert the segment row appears with `#1` and `5 on / 2 off`, and the card updates to `7 days`.
  8. Assert via API detail that the segment exists.
  9. Delete the segment via the row trash icon.
  10. Assert the segment row disappears and the API detail no longer includes it.

### TC-WS-TEAM-001 — Create a team
- **Steps:**
  1. Seed `SQA Team Schedule`, one shift, one rotation, and one segment via API.
  2. Navigate to the schedule detail page and open `Teams`.
  3. Click `New Team`.
  4. Fill Name = `SQA Team A`, Description = `SQA first team`, select the seeded rotation, set Rotation Start Date = `2026-05-13`.
  5. Save.
  6. Assert the team card appears with `starts 2026-05-13` and `0 members`.
  7. Assert via API detail that the team exists with the expected `rotation_id` and `rotation_start`.

### TC-WS-TEAM-002 — Edit a team
- **Steps:**
  1. Seed `SQA Team Schedule`, one shift, one rotation, one segment, and `SQA Team A` via API.
  2. Navigate to `Teams`.
  3. Click Edit.
  4. Change Name to `SQA Team B`, Description to `SQA updated team`, Rotation Start Date to `2026-05-20`.
  5. Save.
  6. Assert the team card updates and API detail reflects the new values.

### TC-WS-TEAM-003 — Delete a team
- **Steps:**
  1. Seed `SQA Team Schedule`, one shift, one rotation, one segment, and `SQA Team A` via API.
  2. Navigate to `Teams`.
  3. Click Delete and accept the confirm dialog.
  4. Assert the team card disappears.
  5. Assert via API detail that the team is no longer present.

### TC-WS-TEAM-004 — Add and remove a member
- **Steps:**
  1. Seed `SQA Team Schedule`, one shift, one rotation, one segment, and `SQA Team A` via API.
  2. Create a temporary auth user `sqa-team-user` via API.
  3. Navigate to `Teams` and expand the team card.
  4. Click `Add Member`.
  5. Enter Username = `sqa-team-user`.
  6. Save.
  7. Assert the member row appears with the resolved full name and username.
  8. Assert via API detail that the team member exists.
  9. Delete the member via the row trash icon.
  10. Assert the member row disappears and the API detail no longer includes it.
