"""
SQA-DT -- Product BOM editor CRUD tests.

Surfaces:
- DT-CLIENT /products/:productId/boms page
- MES REST API /api/v1/products/{productId}/boms
- MES REST API /api/v1/boms/{bomId}/items

Pattern:
- setup and cleanup via API
- UI action via Playwright
- API oracle after each UI mutation
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from playwright.async_api import Page, expect

API_PRODUCTS = "/products"
API_UOM = "/uom"
API_MATERIALS = "/materials"


def _unique_product_code() -> str:
    return f"SQA_PROD_{uuid4().hex[:8]}"


def _unique_material_code() -> str:
    return f"SQA_MAT_{uuid4().hex[:8]}"


def _unique_uom_symbol(prefix: str = "SQA_B") -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _create_scalar_uom(api, *, symbol: str, name: str, uom_type: str = "count") -> dict:
    resp = api.post(
        API_UOM,
        json={
            "symbol": symbol,
            "name": name,
            "uom_type": uom_type,
            "uom_class": "scalar",
            "multiplier": 1.0,
            "offset": 0.0,
        },
    )
    assert resp.status_code in (200, 201), f"UoM setup failed: {resp.text}"
    return resp.json()["data"]


def _create_product(api, *, uom_id: str, **overrides) -> dict:
    payload = {
        "code": _unique_product_code(),
        "name": "SQA BOM Product",
        "version": "1.0",
        "description": "SQA product for BOM tests",
        "uom_id": uom_id,
        "product_type": "discrete",
    }
    payload.update(overrides)
    resp = api.post(API_PRODUCTS, json=payload)
    assert resp.status_code in (200, 201), f"Product setup failed: {resp.text}"
    return resp.json()["data"]


def _create_material(api, *, uom_id: str, **overrides) -> dict:
    payload = {
        "code": _unique_material_code(),
        "name": "SQA BOM Material",
        "description": "SQA material for BOM tests",
        "material_type": "raw",
        "uom_id": uom_id,
    }
    payload.update(overrides)
    resp = api.post(API_MATERIALS, json=payload)
    assert resp.status_code in (200, 201), f"Material setup failed: {resp.text}"
    return resp.json()["data"]


def _create_bom(api, *, product_id: str, **overrides) -> dict:
    payload = {
        "version": "1.0",
        "effective_date": None,
        "expiry_date": None,
    }
    payload.update(overrides)
    resp = api.post(f"{API_PRODUCTS}/{product_id}/boms", json=payload)
    assert resp.status_code in (200, 201), f"BOM setup failed: {resp.text}"
    return resp.json()["data"]


def _create_route(api, *, product_id: str, **overrides) -> dict:
    payload = {
        "name": "SQA BOM Route",
        "version": "1.0",
        "description": "SQA route for BOM step assignment",
        "is_default": True,
    }
    payload.update(overrides)
    resp = api.post(f"{API_PRODUCTS}/{product_id}/operations-definitions", json=payload)
    assert resp.status_code in (200, 201), f"Route setup failed: {resp.text}"
    return resp.json()["data"]


def _create_step(api, *, route_id: str, **overrides) -> dict:
    payload = {
        "sequence": 10,
        "name": "SQA Mix",
        "step_type": "production",
        "expected_cycle_time_sec": 60,
        "is_initial_step": True,
        "input_disposition_ids": [],
        "output_disposition_ids": [],
    }
    payload.update(overrides)
    resp = api.post(f"/operations-definitions/{route_id}/process-segments", json=payload)
    assert resp.status_code in (200, 201), f"Step setup failed: {resp.text}"
    return resp.json()["data"]


def _create_bom_item(api, *, bom_id: str, material_code: str, uom_id: str, **overrides) -> dict:
    payload = {
        "material_code": material_code,
        "quantity": 2.0,
        "uom_id": uom_id,
        "position": 10,
        "process_segment_id": None,
    }
    payload.update(overrides)
    resp = api.post(f"/boms/{bom_id}/items", json=payload)
    assert resp.status_code in (200, 201), f"BOM item setup failed: {resp.text}"
    return resp.json()["data"]


async def _open_bom_editor(page: Page, *, product_id: str) -> None:
    await page.goto(f"http://localhost:5177/products/{product_id}/boms")
    await expect(page.get_by_role("heading", name="Bills of Material")).to_be_visible(timeout=10_000)


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "material_cleanup", "uom_cleanup")
async def test_bom_create(page: Page, api) -> None:
    uom = _create_scalar_uom(api, symbol=_unique_uom_symbol(), name="SQA BOM Each")
    product = _create_product(api, uom_id=uom["id"])

    await _open_bom_editor(page, product_id=product["id"])
    await page.get_by_role("button", name="New BOM").click()
    await expect(page.get_by_role("heading", name="New BOM")).to_be_visible(timeout=5_000)

    await page.locator("input[name='version']").fill("2.0")
    await page.locator("input[name='effective_date']").fill("2026-05-13")
    await page.locator("input[name='expiry_date']").fill("2026-12-31")
    await page.locator("button[type='submit']").click()

    await expect(page.get_by_text("Version 2.0")).to_be_visible(timeout=8_000)
    await expect(page.get_by_text("Effective 2026-05-13", exact=False)).to_be_visible(timeout=8_000)

    resp = api.get(f"{API_PRODUCTS}/{product['id']}/boms", params={"limit": "200"})
    assert resp.status_code == 200, resp.text
    items = resp.json()["data"]
    created = next((item for item in items if item["version"] == "2.0"), None)
    assert created is not None
    assert created["effective_date"] == "2026-05-13"
    assert created["expiry_date"] == "2026-12-31"


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "material_cleanup", "uom_cleanup")
async def test_bom_edit(page: Page, api) -> None:
    uom = _create_scalar_uom(api, symbol=_unique_uom_symbol(), name="SQA BOM Each")
    product = _create_product(api, uom_id=uom["id"])
    bom = _create_bom(api, product_id=product["id"], version="1.0", effective_date="2026-01-01")

    await _open_bom_editor(page, product_id=product["id"])

    row = page.locator("div").filter(has_text="Version 1.0").filter(has_text="Effective 2026-01-01").first
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit BOM")).to_be_visible(timeout=5_000)

    await page.locator("input[name='version']").fill("1.1")
    await page.locator("input[name='expiry_date']").fill("2026-11-30")
    await page.locator("button[type='submit']").click()

    await expect(page.get_by_text("Version 1.1")).to_be_visible(timeout=8_000)

    resp = api.get(f"/boms/{bom['id']}")
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]
    assert updated["version"] == "1.1"
    assert updated["effective_date"] == "2026-01-01"
    assert updated["expiry_date"] == "2026-11-30"


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "material_cleanup", "uom_cleanup")
async def test_bom_delete(page: Page, api) -> None:
    uom = _create_scalar_uom(api, symbol=_unique_uom_symbol(), name="SQA BOM Each")
    product = _create_product(api, uom_id=uom["id"])
    bom = _create_bom(api, product_id=product["id"], version="9.9")

    await _open_bom_editor(page, product_id=product["id"])

    row = page.locator("div").filter(has_text="Version 9.9").first
    await expect(row).to_be_visible(timeout=8_000)

    page.on("dialog", lambda dialog: dialog.accept())
    await row.get_by_title("Delete").click()

    await expect(page.get_by_text("Version 9.9")).to_be_hidden(timeout=8_000)

    resp = api.get(f"/boms/{bom['id']}")
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}: {resp.text}"


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "material_cleanup", "uom_cleanup")
async def test_bom_item_create(page: Page, api) -> None:
    product_uom = _create_scalar_uom(api, symbol=_unique_uom_symbol("SQA_BP"), name="SQA Product Each")
    material_uom = _create_scalar_uom(api, symbol=_unique_uom_symbol("SQA_BM"), name="SQA Material Kilogram", uom_type="mass")
    product = _create_product(api, uom_id=product_uom["id"])
    bom = _create_bom(api, product_id=product["id"], version="4.0")
    material = _create_material(api, uom_id=material_uom["id"], name="SQA Flour")

    await _open_bom_editor(page, product_id=product["id"])
    await expect(page.get_by_text("Items for BOM v4.0")).to_be_visible(timeout=8_000)

    await page.get_by_role("button", name="Add Item").click()
    await expect(page.get_by_role("heading", name="New BOM Item")).to_be_visible(timeout=5_000)
    await page.locator("select[name='material_code']").select_option(value=material["code"])
    await page.locator("input[name='quantity']").fill("5.5")
    await page.locator("select[name='uom_id']").select_option(value=material_uom["id"])
    await page.locator("input[name='position']").fill("20")
    await page.locator("button[type='submit']").click()

    row = page.locator("tr").filter(has_text=material["code"])
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text="5.5")).to_be_visible()

    resp = api.get(f"/boms/{bom['id']}/items", params={"limit": "200"})
    assert resp.status_code == 200, resp.text
    items = resp.json()["data"]
    created = next((item for item in items if item["material_code"] == material["code"]), None)
    assert created is not None
    assert created["quantity"] == 5.5
    assert created["position"] == 20
    assert created["uom_id"] == material_uom["id"]


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "material_cleanup", "uom_cleanup")
async def test_bom_item_edit(page: Page, api) -> None:
    product_uom = _create_scalar_uom(api, symbol=_unique_uom_symbol("SQA_BP"), name="SQA Product Each")
    material_uom = _create_scalar_uom(api, symbol=_unique_uom_symbol("SQA_BM"), name="SQA Material Kilogram", uom_type="mass")
    updated_material_uom = _create_scalar_uom(api, symbol=_unique_uom_symbol("SQA_BU"), name="SQA Material Count")
    product = _create_product(api, uom_id=product_uom["id"])
    bom = _create_bom(api, product_id=product["id"], version="5.0")
    material = _create_material(api, uom_id=material_uom["id"], name="SQA Resin")
    updated_material = _create_material(api, uom_id=updated_material_uom["id"], name="SQA Solvent")
    item = _create_bom_item(api, bom_id=bom["id"], material_code=material["code"], uom_id=material_uom["id"])

    await _open_bom_editor(page, product_id=product["id"])

    row = page.locator("tr").filter(has_text=material["code"])
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit BOM Item")).to_be_visible(timeout=5_000)

    await page.locator("select[name='material_code']").select_option(value=updated_material["code"])
    await page.locator("input[name='quantity']").fill("7.25")
    await page.locator("select[name='uom_id']").select_option(value=updated_material_uom["id"])
    await page.locator("input[name='position']").fill("30")
    await page.locator("button[type='submit']").click()

    updated_row = page.locator("tr").filter(has_text=updated_material["code"])
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.locator("td", has_text="7.25")).to_be_visible()

    resp = api.get(f"/bom-items/{item['id']}")
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]
    assert updated["material_code"] == updated_material["code"]
    assert updated["quantity"] == 7.25
    assert updated["position"] == 30
    assert updated["uom_id"] == updated_material_uom["id"]


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "material_cleanup", "uom_cleanup")
async def test_bom_item_delete(page: Page, api) -> None:
    product_uom = _create_scalar_uom(api, symbol=_unique_uom_symbol("SQA_BP"), name="SQA Product Each")
    material_uom = _create_scalar_uom(api, symbol=_unique_uom_symbol("SQA_BM"), name="SQA Material Kilogram", uom_type="mass")
    product = _create_product(api, uom_id=product_uom["id"])
    bom = _create_bom(api, product_id=product["id"], version="6.0")
    material = _create_material(api, uom_id=material_uom["id"], name="SQA Adhesive")
    item = _create_bom_item(api, bom_id=bom["id"], material_code=material["code"], uom_id=material_uom["id"])

    await _open_bom_editor(page, product_id=product["id"])

    row = page.locator("tr").filter(has_text=material["code"])
    await expect(row).to_be_visible(timeout=8_000)

    page.on("dialog", lambda dialog: dialog.accept())
    await row.get_by_title("Delete").click()

    await expect(page.locator("td", has_text=material["code"])).to_be_hidden(timeout=8_000)

    resp = api.get(f"/bom-items/{item['id']}")
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}: {resp.text}"


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "material_cleanup", "uom_cleanup")
async def test_bom_item_assign_to_real_route_step(page: Page, api) -> None:
    product_uom = _create_scalar_uom(api, symbol=_unique_uom_symbol("SQA_BP"), name="SQA Product Each")
    material_uom = _create_scalar_uom(api, symbol=_unique_uom_symbol("SQA_BM"), name="SQA Material Kilogram", uom_type="mass")
    product = _create_product(api, uom_id=product_uom["id"])
    route = _create_route(api, product_id=product["id"], name="SQA Assigned Route", is_default=True)
    step = _create_step(api, route_id=route["id"], sequence=10, name="SQA Blend")
    bom = _create_bom(api, product_id=product["id"], version="8.0")
    material = _create_material(api, uom_id=material_uom["id"], name="SQA Catalyst")

    await _open_bom_editor(page, product_id=product["id"])
    await expect(page.get_by_text("Items for BOM v8.0")).to_be_visible(timeout=8_000)

    await page.get_by_role("button", name="Add Item").click()
    await expect(page.get_by_role("heading", name="New BOM Item")).to_be_visible(timeout=5_000)
    await page.locator("select[name='material_code']").select_option(value=material["code"])
    await page.locator("input[name='quantity']").fill("3")
    await page.locator("select[name='uom_id']").select_option(value=material_uom["id"])
    await page.locator("input[name='position']").fill("40")
    await page.locator("select[name='process_segment_id']").select_option(value=step["id"])
    await page.locator("button[type='submit']").click()

    row = page.locator("tr").filter(has_text=material["code"])
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text="10. SQA Blend")).to_be_visible()

    resp = api.get(f"/boms/{bom['id']}/items", params={"limit": "200"})
    assert resp.status_code == 200, resp.text
    created = next((item for item in resp.json()["data"] if item["material_code"] == material["code"]), None)
    assert created is not None
    assert created["process_segment_id"] == step["id"]

    step_resp = api.get(f"/process-segments/{step['id']}/bom-items")
    assert step_resp.status_code == 200, step_resp.text
    step_items = step_resp.json()["data"]
    assert any(item["material_code"] == material["code"] for item in step_items)