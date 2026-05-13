"""
SQA-DT -- Materials CRUD tests.

Surfaces:
- DT-CLIENT /materials page
- MES REST API /api/v1/materials

Pattern:
- setup and cleanup via API
- UI action via Playwright
- API oracle after each UI mutation
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from playwright.async_api import Page, expect

DT_MATERIALS_URL = "http://localhost:5177/materials"
API_MATERIALS = "/materials"
API_UOM = "/uom"


def _unique_code(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _create_scalar_uom(
    api,
    *,
    symbol: str,
    name: str,
    uom_type: str = "count",
    multiplier: float = 1.0,
    offset: float = 0.0,
) -> dict:
    resp = api.post(
        API_UOM,
        json={
            "symbol": symbol,
            "name": name,
            "uom_type": uom_type,
            "uom_class": "scalar",
            "multiplier": multiplier,
            "offset": offset,
        },
    )
    assert resp.status_code in (200, 201), f"UoM setup failed: {resp.text}"
    return resp.json()["data"]


def _create_material(api, *, uom_id: str, **overrides) -> dict:
    payload = {
        "code": _unique_code("SQA_MAT"),
        "name": "SQA Material",
        "description": "SQA seeded material",
        "material_type": "raw",
        "uom_id": uom_id,
        "shelf_life_days": 30,
    }
    payload.update(overrides)
    resp = api.post(API_MATERIALS, json=payload)
    assert resp.status_code in (200, 201), f"Material setup failed: {resp.text}"
    return resp.json()["data"]


async def _open_materials_page(page: Page) -> None:
    await page.goto(DT_MATERIALS_URL)
    await expect(page.get_by_role("heading", name="Materials")).to_be_visible(timeout=10_000)


@pytest.mark.ui
@pytest.mark.usefixtures("uom_cleanup", "material_cleanup")
async def test_material_crud(page: Page, api) -> None:
    uom = _create_scalar_uom(api, symbol=_unique_code("SQA_UOM"), name="SQA Material UoM")
    code = _unique_code("SQA_MAT")

    await _open_materials_page(page)
    await page.get_by_role("button", name="New Material").click()
    await expect(page.get_by_role("heading", name="New Material")).to_be_visible(timeout=5_000)

    await page.locator("input[name='code']").fill(code)
    await page.locator("select[name='material_type']").select_option("raw")
    await page.locator("input[name='name']").fill("SQA Resin")
    await page.locator("select[name='uom_id']").select_option(uom["id"])
    await page.locator("input[name='shelf_life_days']").fill("45")
    await page.locator("textarea[name='description']").fill("SQA create material path")
    await page.locator("button[type='submit']").click()

    row = page.locator("tr").filter(has_text=code)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text="SQA Resin")).to_be_visible()

    create_resp = api.get(API_MATERIALS, params={"limit": "200"})
    assert create_resp.status_code == 200, create_resp.text
    created = next((item for item in create_resp.json()["data"] if item["code"] == code), None)
    assert created is not None
    assert created["name"] == "SQA Resin"
    assert created["material_type"] == "raw"
    assert created["uom_id"] == uom["id"]
    assert created["shelf_life_days"] == 45
    assert created["description"] == "SQA create material path"

    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Material")).to_be_visible(timeout=5_000)

    await page.locator("select[name='material_type']").select_option("finished")
    await page.locator("input[name='name']").fill("SQA Finished Resin")
    await page.locator("input[name='shelf_life_days']").fill("90")
    await page.locator("textarea[name='description']").fill("SQA edit material path")
    await page.locator("button[type='submit']").click()

    updated_row = page.locator("tr").filter(has_text=code)
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.locator("td", has_text="SQA Finished Resin")).to_be_visible()

    detail_resp = api.get(f"{API_MATERIALS}/{created['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    updated = detail_resp.json()["data"]
    assert updated["name"] == "SQA Finished Resin"
    assert updated["material_type"] == "finished"
    assert updated["shelf_life_days"] == 90
    assert updated["description"] == "SQA edit material path"

    page.on("dialog", lambda dialog: dialog.accept())
    await updated_row.get_by_title("Delete").click()

    await expect(page.locator("td", has_text=code)).to_be_hidden(timeout=8_000)

    delete_resp = api.get(f"{API_MATERIALS}/{created['id']}")
    assert delete_resp.status_code == 404, (
        f"Expected 404 after delete, got {delete_resp.status_code}: {delete_resp.text}"
    )