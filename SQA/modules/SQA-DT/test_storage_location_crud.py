"""
SQA-DT -- Storage Location CRUD tests.

Surfaces:
- DT-CLIENT /storage-locations page
- MES REST API /api/v1/storage-locations

Pattern:
- setup and cleanup via API
- UI action via Playwright
- API oracle after each UI mutation
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from playwright.async_api import Page, expect

import os
_DT_BASE = os.environ.get("SQA_DT_URL", "http://localhost:5177")
DT_STORAGE_LOCATIONS_URL = f"{_DT_BASE}/storage-locations"
API_STORAGE_LOCATIONS = "/storage-locations"


def _unique_code(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _create_storage_location(api, **overrides):
    payload = {
        "code": _unique_code("SQA_SL"),
        "name": "SQA Storage Location",
        "description": "SQA seeded storage location",
        "location_type": "storage",
        "aisle": "A1",
        "bay": "B1",
        "tier": "T1",
        "site_id": None,
        "capacity": 100.0,
    }
    payload.update(overrides)
    resp = api.post(API_STORAGE_LOCATIONS, json=payload)
    assert resp.status_code in (200, 201), f"Storage location setup failed: {resp.text}"
    return resp.json()["data"]


def _find_storage_location_by_code(api, code: str):
    resp = api.get(API_STORAGE_LOCATIONS, params={"limit": "200"})
    assert resp.status_code == 200, f"List storage locations failed: {resp.text}"
    for item in resp.json().get("data", []):
        if item.get("code") == code:
            return item
    return None


@pytest.fixture(autouse=False)
def storage_location_cleanup(api):
    def _delete_sqa_storage_locations() -> None:
        resp = api.get(API_STORAGE_LOCATIONS, params={"limit": "200"})
        if resp.status_code != 200:
            return
        for item in resp.json().get("data", []):
            if item.get("code", "").startswith("SQA_SL_"):
                api.delete(f"{API_STORAGE_LOCATIONS}/{item['id']}")

    _delete_sqa_storage_locations()
    yield
    _delete_sqa_storage_locations()


async def _open_storage_locations_page(page: Page) -> None:
    await page.goto(DT_STORAGE_LOCATIONS_URL)
    await expect(
        page.get_by_role("heading", name="Storage Locations")
    ).to_be_visible(timeout=10_000)


@pytest.mark.ui
@pytest.mark.usefixtures("storage_location_cleanup")
async def test_storage_location_crud(page: Page, api) -> None:
    code = _unique_code("SQA_SL")

    await _open_storage_locations_page(page)
    await page.get_by_role("button", name="New Location").click()
    await expect(
        page.get_by_role("heading", name="New Storage Location")
    ).to_be_visible(timeout=5_000)

    await page.locator("input[name='code']").fill(code)
    await page.locator("input[name='name']").fill("SQA Main Warehouse")
    await page.locator("textarea[name='description']").fill("SQA create location path")
    await page.locator("select[name='location_type']").select_option("storage")
    await page.locator("input[name='aisle']").fill("A3")
    await page.locator("input[name='bay']").fill("B7")
    await page.locator("input[name='tier']").fill("T2")
    await page.locator("input[name='capacity']").fill("150.5")
    await page.locator("button[type='submit']").click()

    row = page.locator("tr").filter(has_text=code)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text="SQA Main Warehouse")).to_be_visible()

    created = _find_storage_location_by_code(api, code)
    assert created is not None
    assert created["name"] == "SQA Main Warehouse"
    assert created["description"] == "SQA create location path"
    assert created["location_type"] == "storage"
    assert created["aisle"] == "A3"
    assert created["bay"] == "B7"
    assert created["tier"] == "T2"
    assert created["capacity"] == 150.5

    await row.get_by_title("Edit").click()
    await expect(
        page.get_by_role("heading", name="Edit Storage Location")
    ).to_be_visible(timeout=5_000)

    await page.locator("input[name='name']").fill("SQA Shipping Dock")
    await page.locator("textarea[name='description']").fill("SQA edit location path")
    await page.locator("select[name='location_type']").select_option("shipping")
    await page.locator("input[name='aisle']").fill("C1")
    await page.locator("input[name='bay']").fill("D2")
    await page.locator("input[name='tier']").fill("E3")
    await page.locator("input[name='capacity']").fill("225")
    await page.locator("button[type='submit']").click()

    updated_row = page.locator("tr").filter(has_text=code)
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.locator("td", has_text="SQA Shipping Dock")).to_be_visible()

    detail_resp = api.get(f"{API_STORAGE_LOCATIONS}/{created['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    updated = detail_resp.json()["data"]
    assert updated["name"] == "SQA Shipping Dock"
    assert updated["description"] == "SQA edit location path"
    assert updated["location_type"] == "shipping"
    assert updated["aisle"] == "C1"
    assert updated["bay"] == "D2"
    assert updated["tier"] == "E3"
    assert updated["capacity"] == 225

    page.on("dialog", lambda dialog: dialog.accept())
    await updated_row.get_by_title("Delete").click()

    await expect(page.locator("td", has_text=code)).to_be_hidden(timeout=8_000)

    delete_resp = api.get(f"{API_STORAGE_LOCATIONS}/{created['id']}")
    assert delete_resp.status_code == 404, (
        f"Expected 404 after delete, got {delete_resp.status_code}: {delete_resp.text}"
    )