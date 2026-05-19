"""
SQA-DT — UoM CRUD editor tests.

Source of truth: SQA/plans/SQA-DT.md
Surfaces: DT-CLIENT /uom page + MES REST API /api/v1/uom

Authoring rules (enforced):
- Selectors use HTML name attrs / radio values / CSS siblings — no CSS classes.
- Every UI action is followed by an API oracle confirming persistence.
- Setup and teardown use the REST API (conftest uom_cleanup fixture).
- Server: http://localhost:8082  DT-CLIENT: http://localhost:5173

Implementation notes:
- Headless UI <Dialog> root div is CSS-invisible (no bounding box); check the
  inner heading instead of the dialog role for visibility assertions.
- react-hook-form register() spreads name= attr onto inputs/selects → reliable
  selectors: input[name='symbol'], select[name='uom_type'], etc.
- Radio buttons use Controller (no name attr) → select by value attr.
- DB may not be seeded → composite tests create their own SQA_* base scalars.
"""
from __future__ import annotations

import pytest
from playwright.async_api import Page, expect

import os
_DT_BASE = os.environ.get("SQA_DT_URL", "http://localhost:5177")
DT_UOM_URL = f"{_DT_BASE}/uom"
API_UOM    = "/uom"          # relative to conftest api.base_url


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _open_uom_page(page: Page) -> None:
    """Navigate to the UoM list page and wait for the heading."""
    await page.goto(DT_UOM_URL)
    await expect(page.get_by_role("heading", name="Units of Measure")).to_be_visible(timeout=10_000)


async def _open_new_unit_dialog(page: Page) -> None:
    """Click 'New Unit' and wait for the dialog title (not the Headless UI root div)."""
    await page.get_by_role("button", name="New Unit").click()
    await expect(page.get_by_role("heading", name="New Unit of Measure")).to_be_visible(timeout=5_000)


async def _fill_scalar_form(page: Page, *, symbol: str, name: str,
                             uom_type: str = "Mass") -> None:
    """Fill the UoM form for a scalar unit.  uom_type is the label text (e.g. 'Mass').

    Uses react-hook-form name= attributes and radio value= attrs for reliable selection.
    """
    await page.locator("input[type='radio'][value='scalar']").click()
    await page.locator("input[name='symbol']").fill(symbol)
    await page.locator("input[name='name']").fill(name)
    await page.locator("select[name='uom_type']").select_option(label=uom_type)


async def _submit_dialog(page: Page, *, edit: bool = False) -> None:
    """Click the submit button (Create / Update) inside the open dialog."""
    await page.locator("button[type='submit']").click()


def _api_get_by_symbol(api, symbol: str):
    """Return the httpx response for GET /uom/symbol/{symbol}."""
    return api.get(f"{API_UOM}/symbol/{symbol}")


def _create_scalar(api, symbol: str, name: str, uom_type: str) -> None:
    """Create a scalar UoM via API and assert success (200 or 201)."""
    resp = api.post(API_UOM, json={
        "symbol": symbol, "name": name,
        "uom_type": uom_type, "uom_class": "scalar",
        "multiplier": 1.0, "offset": 0.0,
    })
    assert resp.status_code in (200, 201), f"API setup failed ({symbol}): {resp.text}"


# ─── TC-UOM-001: Create a scalar unit ────────────────────────────────────────

@pytest.mark.ui
@pytest.mark.usefixtures("uom_cleanup")
async def test_uom_create_scalar(page: Page, api) -> None:
    """TC-UOM-001 — Create a new scalar mass unit via the UI and verify via API."""
    symbol = "SQA_kg2"
    name   = "SQA Test Kilogram"

    await _open_uom_page(page)
    await _open_new_unit_dialog(page)
    await _fill_scalar_form(page, symbol=symbol, name=name, uom_type="Mass")
    await _submit_dialog(page)

    # UI oracle: new row appears in table
    await expect(page.locator("td", has_text=symbol).first).to_be_visible(timeout=8_000)

    # API oracle: row persisted
    resp = _api_get_by_symbol(api, symbol)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()["data"]
    assert data["symbol"]    == symbol
    assert data["name"]      == name
    assert data["uom_type"]  == "mass"
    assert data["uom_class"] == "scalar"


# ─── TC-UOM-002: Edit a scalar unit ──────────────────────────────────────────

@pytest.mark.ui
@pytest.mark.usefixtures("uom_cleanup")
async def test_uom_edit_scalar(page: Page, api) -> None:
    """TC-UOM-002 — Edit an existing scalar unit via the UI and verify via API."""
    symbol   = "SQA_kg2"
    name     = "SQA Test Kilogram"
    new_name = "SQA Test Kilogram Edited"

    # Setup: create via API so we're not testing create here
    _create_scalar(api, symbol, name, "mass")

    await _open_uom_page(page)

    # Find row by symbol text; click Edit button (title="Edit")
    row = page.locator("tr").filter(has_text=symbol)
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Edit").click()
    # Check inner dialog heading (Headless UI outer div has no bounding box)
    await expect(page.get_by_role("heading", name="Edit Unit")).to_be_visible(timeout=5_000)

    # Change the name
    name_field = page.locator("input[name='name']")
    await name_field.clear()
    await name_field.fill(new_name)
    await _submit_dialog(page, edit=True)

    # UI oracle: table row shows updated name
    await expect(page.locator("td", has_text=new_name).first).to_be_visible(timeout=8_000)

    # API oracle
    resp = _api_get_by_symbol(api, symbol)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == new_name


# ─── TC-UOM-003: Delete a non-built-in unit ──────────────────────────────────

@pytest.mark.ui
@pytest.mark.usefixtures("uom_cleanup")
async def test_uom_delete(page: Page, api) -> None:
    """TC-UOM-003 — Delete a user-created unit via the UI and verify via API (404)."""
    symbol = "SQA_kg2"
    name   = "SQA Test Kilogram"

    # Setup via API
    _create_scalar(api, symbol, name, "mass")

    await _open_uom_page(page)

    row = page.locator("tr").filter(has_text=symbol)
    await expect(row).to_be_visible(timeout=8_000)

    # Accept browser confirm() dialog, then click Delete
    page.on("dialog", lambda d: d.accept())
    await row.get_by_title("Delete").click()

    # UI oracle: row disappears
    await expect(page.locator("td", has_text=symbol)).to_be_hidden(timeout=8_000)

    # API oracle: soft-deleted → 404
    resp = _api_get_by_symbol(api, symbol)
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}"


# ─── TC-UOM-004: Create a quotient composite unit ────────────────────────────

@pytest.mark.ui
@pytest.mark.usefixtures("uom_cleanup")
async def test_uom_create_quotient(page: Page, api) -> None:
    """TC-UOM-004 — Create a quotient unit (SQA_len_m ÷ SQA_time_s) via the UI."""
    # Create base scalars first (DB may not be seeded)
    _create_scalar(api, "SQA_len_m",  "SQA Metre",  "length")
    _create_scalar(api, "SQA_time_s", "SQA Second", "time")

    symbol = "SQA_mps"
    name   = "SQA Metres per Second"

    await _open_uom_page(page)
    await _open_new_unit_dialog(page)

    # Select Quotient class radio
    await page.locator("input[type='radio'][value='quotient']").click()
    await page.locator("input[name='symbol']").fill(symbol)
    await page.locator("input[name='name']").fill(name)
    await page.locator("select[name='uom_type']").select_option(label="Length")
    # ComponentSelector fields use react-hook-form name attrs directly
    await page.locator("select[name='left_uom_symbol']").select_option(value="SQA_len_m")
    await page.locator("select[name='right_uom_symbol']").select_option(value="SQA_time_s")
    await _submit_dialog(page)

    # UI oracle: symbol and formula columns visible
    await expect(page.locator("td", has_text=symbol).first).to_be_visible(timeout=8_000)
    await expect(page.locator("td", has_text="SQA_len_m \u00f7 SQA_time_s").first).to_be_visible(timeout=5_000)

    # API oracle
    resp = _api_get_by_symbol(api, symbol)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()["data"]
    assert data["uom_class"]        == "quotient"
    assert data["left_uom_symbol"]  == "SQA_len_m"
    assert data["right_uom_symbol"] == "SQA_time_s"


# ─── TC-UOM-006: Type filter narrows table ───────────────────────────────────

@pytest.mark.ui
@pytest.mark.usefixtures("uom_cleanup")
async def test_uom_type_filter(page: Page, api) -> None:
    """TC-UOM-006 — Type filter shows only matching rows.

    Uses made-up SQA units (SQA_one, SQA_two) under the 'custom' type so the
    test has no dependency on seeded data or specific ISA-95 type categories.
    """
    _create_scalar(api, "SQA_one", "One",  "custom")
    _create_scalar(api, "SQA_two", "Two",  "custom")

    await _open_uom_page(page)

    # The filter <select> has no htmlFor; use CSS adjacent-sibling of its <label>
    filter_select = page.locator("label:has-text('Filter by type:') + select")

    # Filter by Custom → both SQA units visible
    await filter_select.select_option(label="Custom")
    await expect(page.locator("td", has_text="SQA_one").first).to_be_visible(timeout=5_000)
    await expect(page.locator("td", has_text="SQA_two").first).to_be_visible(timeout=5_000)

    # Filter by Mass → neither SQA unit visible (they are custom, not mass)
    await filter_select.select_option(label="Mass")
    await expect(page.locator("td", has_text="SQA_one")).to_be_hidden()
    await expect(page.locator("td", has_text="SQA_two")).to_be_hidden()

    # Clear filter → both SQA units visible again
    await filter_select.select_option(value="")
    await expect(page.locator("td", has_text="SQA_one").first).to_be_visible(timeout=5_000)
    await expect(page.locator("td", has_text="SQA_two").first).to_be_visible(timeout=5_000)


# ─── TC-UOM-007: Create a product composite unit ────────────────────────────

@pytest.mark.ui
@pytest.mark.usefixtures("uom_cleanup")
async def test_uom_create_product(page: Page, api) -> None:
    """TC-UOM-007 — Create a product unit (SQA_mass_kg × SQA_len_m) via the UI."""
    _create_scalar(api, "SQA_mass_kg", "SQA Kilogram", "mass")
    _create_scalar(api, "SQA_len_m",   "SQA Metre",   "length")

    symbol = "SQA_kgm"
    name   = "SQA Kilogram Metre"

    await _open_uom_page(page)
    await _open_new_unit_dialog(page)

    await page.locator("input[type='radio'][value='product']").click()
    await page.locator("input[name='symbol']").fill(symbol)
    await page.locator("input[name='name']").fill(name)
    await page.locator("select[name='uom_type']").select_option(label="Custom")
    await page.locator("select[name='left_uom_symbol']").select_option(value="SQA_mass_kg")
    await page.locator("select[name='right_uom_symbol']").select_option(value="SQA_len_m")
    await _submit_dialog(page)

    await expect(page.locator("td", has_text=symbol).first).to_be_visible(timeout=8_000)

    # API oracle
    resp = _api_get_by_symbol(api, symbol)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()["data"]
    assert data["uom_class"]        == "product"
    assert data["left_uom_symbol"]  == "SQA_mass_kg"
    assert data["right_uom_symbol"] == "SQA_len_m"


# ─── TC-UOM-008: Create a power composite unit ────────────────────────────────

@pytest.mark.ui
@pytest.mark.usefixtures("uom_cleanup")
async def test_uom_create_power(page: Page, api) -> None:
    """TC-UOM-008 — Create a power unit (SQA_len_m ^ 3) via the UI."""
    _create_scalar(api, "SQA_len_m", "SQA Metre", "length")

    symbol = "SQA_m3"
    name   = "SQA Cubic Metre"

    await _open_uom_page(page)
    await _open_new_unit_dialog(page)

    await page.locator("input[type='radio'][value='power']").click()
    await page.locator("input[name='symbol']").fill(symbol)
    await page.locator("input[name='name']").fill(name)
    await page.locator("select[name='uom_type']").select_option(label="Custom")
    await page.locator("select[name='left_uom_symbol']").select_option(value="SQA_len_m")
    await page.locator("input[name='exponent']").fill("3")
    await _submit_dialog(page)

    await expect(page.locator("td", has_text=symbol).first).to_be_visible(timeout=8_000)

    # API oracle
    resp = _api_get_by_symbol(api, symbol)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()["data"]
    assert data["uom_class"]       == "power"
    assert data["left_uom_symbol"] == "SQA_len_m"
    assert data["exponent"]        == 3

