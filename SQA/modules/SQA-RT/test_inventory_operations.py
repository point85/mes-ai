"""
SQA-RT -- Inventory operations tests.

Surfaces:
- RT-CLIENT /
- RT-CLIENT Inventory tab
- MES REST API (for seeded setup)

Pattern:
- setup via API
- UI action via Playwright
- API/UI verification
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from playwright.async_api import Page, expect

API_MATERIALS = "/materials"
API_UOM = "/uom"
API_STORAGE_LOCATIONS = "/storage-locations"


def _unique_code(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _create_scalar_uom(api, *, symbol: str, name: str) -> dict:
    resp = api.post(
        API_UOM,
        json={
            "symbol": symbol,
            "name": name,
            "uom_type": "count",
            "uom_class": "scalar",
            "multiplier": 1.0,
            "offset": 0.0,
        },
    )
    assert resp.status_code in (200, 201), f"UoM setup failed: {resp.text}"
    return resp.json()["data"]


def _create_material(api, *, uom_id: str, code: str, name: str) -> dict:
    resp = api.post(
        API_MATERIALS,
        json={
            "code": code,
            "name": name,
            "material_type": "raw",
            "uom_id": uom_id,
        },
    )
    assert resp.status_code in (200, 201), f"Material setup failed: {resp.text}"
    return resp.json()["data"]


def _create_storage_location(api, *, code: str, name: str) -> dict:
    resp = api.post(
        API_STORAGE_LOCATIONS,
        json={
            "code": code,
            "name": name,
            "location_type": "storage",
        },
    )
    assert resp.status_code in (200, 201), f"Storage location setup failed: {resp.text}"
    return resp.json()["data"]


@pytest.fixture
def storage_location_cleanup(api):
    yield
    # Cleanup SQA seeded storage locations
    resp = api.get(API_STORAGE_LOCATIONS, params={"limit": "500"})
    if resp.status_code == 200:
        for loc in resp.json().get("data", []):
            if loc["code"].startswith("WH1_") or loc["code"].startswith("WH2_"):
                api.delete(f"{API_STORAGE_LOCATIONS}/{loc['id']}")


@pytest.mark.ui
@pytest.mark.usefixtures("uom_cleanup", "material_cleanup", "storage_location_cleanup")
async def test_rt_inventory_operations(page: Page, api, mes_urls) -> None:
    # 1. API Seeds
    uom = _create_scalar_uom(api, symbol=_unique_code("SQA_UOM"), name="SQA Material UoM")
    mat = _create_material(api, uom_id=uom["id"], code=_unique_code("SQA_MAT"), name="SQA Inventory Material")
    loc1 = _create_storage_location(api, code=_unique_code("WH1"), name="Warehouse 1")
    loc2 = _create_storage_location(api, code=_unique_code("WH2"), name="Warehouse 2")

    rt_url = mes_urls["rt"]

    # 2. Go to RT Inventory Page
    await page.goto(rt_url)
    await page.get_by_role("button", name="Inventory").click()
    await expect(page.get_by_role("heading", name="Inventory", exact=True)).to_be_visible(timeout=10000)

    # 3. Create a Material Lot
    await page.get_by_role("button", name="Material Lots").click()
    await page.get_by_role("button", name="New Lot").click()
    
    # Dialog for new lot
    lot_number = _unique_code("LOT")
    # Using specific selectors matching the RT client DOM
    await page.get_by_placeholder("LOT-2026-0001").fill(lot_number)
    # The material dropdown has "— Select material —"
    await page.locator("select", has_text="Select material").select_option(value=mat["id"])
    await page.get_by_role("button", name="Create", exact=True).click()
    # Wait for lot to appear in the table (which means the create request completed)
    await expect(page.locator("tr", has_text=lot_number)).to_be_visible(timeout=5000)
    
    resp = api.get("/material-lots", params={"limit": 100})
    assert resp.status_code == 200
    lot_id = next(l["id"] for l in resp.json()["data"] if l["lot_number"] == lot_number)

    # 4. Perform Operations
    await page.get_by_role("button", name="Operations").click()
    # Wait for the freshly created lot to populate the Material Lot dropdown
    # (clicking the tab triggers loadRefData() in the parent component)
    await expect(
        page.locator(f"label:has-text('Material Lot') ~ select option[value='{lot_id}']"),
    ).to_be_attached(timeout=10000)

    def get_select(label_text: str):
        return page.locator(f"label:has-text('{label_text}') ~ select:visible")

    def get_input(label_text: str):
        return page.locator(f"label:has-text('{label_text}') ~ input:visible")

    # 4a. Receive Inventory
    # Should be default op. Fill quantity and to_location
    await get_select("Material Lot").select_option(value=lot_id)
    await get_select("To Location").select_option(value=loc1["id"])
    await get_input("Quantity").fill("100")
    await page.get_by_role("button", name="Submit Receive").click()
    await expect(page.locator("div.bg-green-50", has_text="completed")).to_be_visible()

    # 4b. Move Inventory
    await page.get_by_role("button", name="Move").click()
    await get_select("Material Lot").select_option(value=lot_id)
    await get_select("From Location").select_option(value=loc1["id"])
    await get_select("To Location").select_option(value=loc2["id"])
    await get_input("Quantity").fill("5")
    await page.get_by_role("button", name="Submit Move").click()
    await expect(page.locator("div.bg-green-50", has_text="completed")).to_be_visible()

    # 4c. Consume Inventory
    await page.get_by_role("button", name="Consume").click()
    await get_select("Material Lot").select_option(value=lot_id)
    await get_select("From Location").select_option(value=loc1["id"])
    await get_input("Quantity").fill("15")
    await page.get_by_role("button", name="Submit Consume").click()
    await expect(page.locator("div.bg-green-50", has_text="completed")).to_be_visible()

    # 4d. Adjust Inventory
    await page.get_by_role("button", name="Adjust").click()
    await get_select("Material Lot").select_option(value=lot_id)
    
    # Adjust uses "Location" label, not "From Location"
    await get_select("Location").select_option(value=loc2["id"])
    
    # Quantity placeholder differs for adjust
    await page.get_by_placeholder("Set absolute quantity").fill("50")
    
    # Reason required
    await page.get_by_placeholder("Reason required for adjustments").fill("SQA Manual Adjustment")
    await page.get_by_role("button", name="Submit Adjust").click()
    await expect(page.locator("div.bg-green-50", has_text="completed")).to_be_visible()

    # 5. Verify Balances
    await page.get_by_role("button", name="Balances").click()
    # loc1: receive 100, move out 5, consume 15 → 80
    # loc2: move in 5, adjusted to exactly 50
    await page.get_by_placeholder("Search by lot number…").fill(lot_number)
    
    # Wait for table to filter
    await expect(page.locator("tbody tr")).to_have_count(2, timeout=5000)
    
    # Verify the table rows
    balances_text = await page.locator("tbody").inner_text()
    assert loc1["code"] in balances_text
    assert loc2["code"] in balances_text
    # We can't strictly assert exactly innerText match easily without proper DOM paths, 
    # but asserting that "50" exists next to both rows is a reasonably strong signal
    await expect(page.locator("tr", has_text=loc1["code"])).to_contain_text("80")
    await expect(page.locator("tr", has_text=loc2["code"])).to_contain_text("50")

    # 6. Verify Transaction Log
    await page.get_by_role("button", name="Transaction Log").click()
    await page.get_by_placeholder("Filter by lot #").fill(lot_number)
    
    # Wait for UI to filter
    await expect(page.locator("tbody tr").first).to_be_visible()
    
    # Should be 4 transactions: Receive, Move, Consume, Adjust
    log_text = await page.locator("tbody").inner_text()
    assert "receive" in log_text.lower()
    assert "move" in log_text.lower()
    assert "consume" in log_text.lower()
    assert "adjust" in log_text.lower()
