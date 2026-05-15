"""
SQA-RT -- Inventory operations tests.

Surfaces:
- RT-CLIENT /
- RT-CLIENT Inventory tab
- MES REST API (for data lookup)

Pattern:
- Look up existing available lot and two storage locations via API
- UI action via Playwright against the RT-CLIENT
- Verify success banners, balances, and transaction log

No seeding or cleanup is required: the test works from the lot's current
balances and asserts the expected deltas.
"""
from __future__ import annotations

import pytest
from playwright.async_api import Page, expect

API_LOTS      = "/material-lots"
API_LOCATIONS = "/storage-locations"
API_BALANCES  = "/inventory/balances"


@pytest.mark.ui
async def test_rt_inventory_operations(page: Page, api, mes_urls) -> None:
    # -- 1. Resolve existing data from the API --------------------------------
    # We use any available lot and compute the expected final balances from its
    # current state so repeated audits do not depend on a pristine DB.
    resp = api.get(API_LOTS, params={"limit": 100})
    assert resp.status_code == 200, f"Could not fetch lots: {resp.text}"
    available_lots = [l for l in resp.json()["data"] if l["status"] == "available"]
    assert available_lots, "No available lots found -- seed the DB first"
    lot = available_lots[0]
    lot_id     = lot["id"]
    lot_number = lot["lot_number"]

    resp = api.get(API_LOCATIONS, params={"limit": 100})
    assert resp.status_code == 200, f"Could not fetch locations: {resp.text}"
    active_locs = [l for l in resp.json()["data"] if l["is_active"]]
    assert len(active_locs) >= 2, "Need at least 2 active storage locations in the database"
    loc1 = active_locs[0]
    loc2 = active_locs[1]

    resp = api.get(API_BALANCES, params={"material_lot_id": lot_id, "limit": 200})
    assert resp.status_code == 200, f"Could not fetch balances: {resp.text}"
    starting_balances = {
        balance["location_id"]: float(balance["quantity_on_hand"])
        for balance in resp.json()["data"]
    }
    starting_loc1 = starting_balances.get(loc1["id"], 0.0)

    rt_url = mes_urls["rt"]

    # -- 2. Navigate to the Inventory page ------------------------------------
    await page.goto(rt_url)
    await page.get_by_role("button", name="Inventory").click()
    await expect(
        page.get_by_role("heading", name="Inventory", exact=True)
    ).to_be_visible(timeout=10_000)

    # -- 3. Open the Operations tab -------------------------------------------
    await page.get_by_role("button", name="Operations").click()
    # Wait until the lot appears in the Material Lot dropdown.
    # Clicking the Operations tab triggers loadRefData() in the parent component.
    await expect(
        page.locator(f"label:has-text('Material Lot') ~ select option[value='{lot_id}']"),
    ).to_be_attached(timeout=10_000)

    def get_select(label_text: str):
        return page.locator(f"label:has-text('{label_text}') ~ select:visible")

    def get_input(label_text: str):
        return page.locator(f"label:has-text('{label_text}') ~ input:visible")

    # -- 4a. Receive -- qty 100 into loc1 -------------------------------------
    await get_select("Material Lot").select_option(value=lot_id)
    await get_select("To Location").select_option(value=loc1["id"])
    await get_input("Quantity").fill("100")
    await page.get_by_role("button", name="Submit Receive").click()
    await expect(page.locator("div.bg-green-50", has_text="completed")).to_be_visible()

    # -- 4b. Move -- 5 units from loc1 to loc2 --------------------------------
    await page.get_by_role("button", name="Move").click()
    await get_select("Material Lot").select_option(value=lot_id)
    await get_select("From Location").select_option(value=loc1["id"])
    await get_select("To Location").select_option(value=loc2["id"])
    await get_input("Quantity").fill("5")
    await page.get_by_role("button", name="Submit Move").click()
    await expect(page.locator("div.bg-green-50", has_text="completed")).to_be_visible()

    # -- 4c. Consume -- 15 units from loc1 ------------------------------------
    await page.get_by_role("button", name="Consume").click()
    await get_select("Material Lot").select_option(value=lot_id)
    await get_select("From Location").select_option(value=loc1["id"])
    await get_input("Quantity").fill("15")
    await page.get_by_role("button", name="Submit Consume").click()
    await expect(page.locator("div.bg-green-50", has_text="completed")).to_be_visible()

    # -- 4d. Adjust -- set loc2 absolute qty to 50 ----------------------------
    await page.get_by_role("button", name="Adjust").click()
    await get_select("Material Lot").select_option(value=lot_id)
    await get_select("Location").select_option(value=loc2["id"])
    await page.get_by_placeholder("Set absolute quantity").fill("50")
    await page.get_by_placeholder("Reason required for adjustments").fill("SQA Manual Adjustment")
    await page.get_by_role("button", name="Submit Adjust").click()
    await expect(page.locator("div.bg-green-50", has_text="completed")).to_be_visible()

    # -- 5. Verify Balances ---------------------------------------------------
    # Expected final state:
    #   loc1: start + receive 100 - move 5 - consume 15 = start + 80
    #   loc2: move in 5, then adjusted to 50
    # NOTE: All pages share the DOM (hidden via CSS), so scope to the Balances
    # panel h3 to avoid matching hidden rows from other page components.
    await page.get_by_role("button", name="Balances").click()
    await page.get_by_placeholder("Search by lot number\u2026").fill(lot_number)
    # Anchor on the Balances heading to scope to the visible panel's table
    bal_tbody = page.locator("h3", has_text="Current Inventory Balances").locator("xpath=following::tbody[1]")
    await expect(bal_tbody.locator("tr", has_text=loc1["code"])).to_be_visible(timeout=5_000)
    await expect(bal_tbody.locator("tr", has_text=loc2["code"])).to_be_visible(timeout=5_000)
    await expect(bal_tbody.locator("tr", has_text=loc1["code"])).to_contain_text(str(int(starting_loc1 + 80)))
    await expect(bal_tbody.locator("tr", has_text=loc2["code"])).to_contain_text("50")

    # -- 6. Verify Transaction Log --------------------------------------------
    # Should show entries for: receive, move, consume, adjust (sorted newest-first).
    # Scope to the Transaction Log panel via its unique h3 to avoid matching
    # hidden tbody rows from other pages (all pages share the DOM via hidden CSS).
    await page.get_by_role("button", name="Transaction Log").click()
    txn_heading = page.locator("h3", has_text="Transaction Log")
    await expect(txn_heading).to_be_visible(timeout=5_000)
    txn_tbody = txn_heading.locator("xpath=following::tbody[1]")
    # Wait for data to load (loading row vanishes when actual rows appear)
    await expect(txn_tbody.locator("td", has_text="Loading\u2026")).to_be_hidden(timeout=10_000)
    log_text = await txn_tbody.inner_text()
    assert "receive" in log_text.lower(), "Receive transaction not found in log"
    assert "move"    in log_text.lower(), "Move transaction not found in log"
    assert "consume" in log_text.lower(), "Consume transaction not found in log"
    assert "adjust"  in log_text.lower(), "Adjust transaction not found in log"
