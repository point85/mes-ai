"""
SQA-DT -- Standalone route editor CRUD tests.

Surfaces:
- DT-CLIENT /routes page
- MES REST API /api/v1/operations-definitions

Pattern:
- setup and cleanup via API
- UI action via Playwright
- API oracle after each UI mutation
"""
from __future__ import annotations

import pytest
from playwright.async_api import Page, expect
from uuid import uuid4

DT_ROUTES_URL = "http://localhost:5177/routes"
API_ROUTES = "/operations-definitions"
API_PRODUCTS = "/products"
API_MATERIALS = "/materials"
API_UOM = "/uom"


async def _open_routes_page(page: Page) -> None:
    await page.goto(DT_ROUTES_URL)
    await expect(page.get_by_role("heading", name="Route Editor")).to_be_visible(timeout=10_000)


def _create_route(api, **overrides):
    payload = {
        "name": "SQA Seeded Route",
        "version": "1.0",
        "description": "SQA seeded standalone route",
        "is_default": False,
    }
    payload.update(overrides)
    resp = api.post(API_ROUTES, json=payload)
    assert resp.status_code in (200, 201), f"Route setup failed: {resp.text}"
    return resp.json()["data"]


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


def _create_product(api, *, uom_id: str, **overrides) -> dict:
    payload = {
        "code": f"SQA_PROD_{uuid4().hex[:8]}",
        "name": "SQA Assigned Product",
        "version": "1.0",
        "description": "SQA product for route assignment tests",
        "uom_id": uom_id,
        "product_type": "discrete",
    }
    payload.update(overrides)
    resp = api.post(API_PRODUCTS, json=payload)
    assert resp.status_code in (200, 201), f"Product setup failed: {resp.text}"
    return resp.json()["data"]


def _create_material(api, *, uom_id: str, **overrides) -> dict:
    payload = {
        "code": f"SQA_MAT_{uuid4().hex[:8]}",
        "name": "SQA Assigned Material",
        "description": "SQA material for route assignment tests",
        "material_type": "raw",
        "uom_id": uom_id,
        "shelf_life_days": 30,
    }
    payload.update(overrides)
    resp = api.post(API_MATERIALS, json=payload)
    assert resp.status_code in (200, 201), f"Material setup failed: {resp.text}"
    return resp.json()["data"]


def _find_route_by_name(api, name: str):
    resp = api.get(API_ROUTES, params={"limit": "200"})
    assert resp.status_code == 200, f"List routes failed: {resp.text}"
    for item in resp.json().get("data", []):
        if item.get("name") == name:
            return item
    return None


async def _select_route(page: Page, *, route_name: str, route_version: str) -> None:
    select_button = page.locator("button").filter(has_text=route_name).filter(has_text=f"v{route_version}").first
    await expect(select_button).to_be_visible(timeout=8_000)
    await select_button.click()
    await expect(page.get_by_text(f"Steps — {route_name}")).to_be_visible(timeout=8_000)


@pytest.mark.ui
@pytest.mark.usefixtures("route_cleanup")
async def test_route_editor_crud(page: Page, api) -> None:
    route_name = "SQA Standalone Route"

    await _open_routes_page(page)
    await page.get_by_role("button", name="New").click()
    await expect(page.get_by_role("heading", name="New Route")).to_be_visible(timeout=5_000)

    await page.locator("input[name='name']").fill(route_name)
    await page.locator("input[name='version']").fill("2.0")
    await page.locator("textarea[name='description']").fill("SQA standalone route create path")
    await page.locator("input[name='is_default']").check()
    await page.locator("button[type='submit']").click()

    route_entry = page.locator("div").filter(has_text=route_name).filter(has_text="v2.0").first
    await expect(route_entry).to_be_visible(timeout=8_000)

    created = _find_route_by_name(api, route_name)
    assert created is not None
    assert created["version"] == "2.0"
    assert created["description"] == "SQA standalone route create path"
    assert created["is_default"] is True

    await route_entry.get_by_title("Edit route").click()
    await expect(page.get_by_role("heading", name="Edit Route")).to_be_visible(timeout=5_000)

    await page.locator("input[name='name']").fill("SQA Standalone Route Updated")
    await page.locator("input[name='version']").fill("2.1")
    await page.locator("textarea[name='description']").fill("SQA standalone route edit path")
    await page.locator("button[type='submit']").click()

    updated_entry = page.locator("div").filter(has_text="SQA Standalone Route Updated").filter(has_text="v2.1").first
    await expect(updated_entry).to_be_visible(timeout=8_000)

    detail_resp = api.get(f"{API_ROUTES}/{created['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    updated = detail_resp.json()["data"]
    assert updated["name"] == "SQA Standalone Route Updated"
    assert updated["version"] == "2.1"
    assert updated["description"] == "SQA standalone route edit path"

    page.on("dialog", lambda dialog: dialog.accept())
    await updated_entry.get_by_title("Delete route").click()

    await expect(page.get_by_text("SQA Standalone Route Updated")).to_be_hidden(timeout=8_000)

    delete_resp = api.get(f"{API_ROUTES}/{created['id']}")
    assert delete_resp.status_code == 404, (
        f"Expected 404 after delete, got {delete_resp.status_code}: {delete_resp.text}"
    )


@pytest.mark.ui
@pytest.mark.usefixtures("route_cleanup")
async def test_route_step_crud(page: Page, api) -> None:
    route = _create_route(api, name="SQA Step Route", version="3.0")

    await _open_routes_page(page)
    await _select_route(page, route_name=route["name"], route_version=route["version"])

    await page.get_by_role("button", name="New Step").click()
    await expect(page.get_by_role("heading", name="New Step")).to_be_visible(timeout=5_000)

    await page.locator("input[name='sequence']").fill("20")
    await page.locator("select[name='step_type']").select_option("inspection")
    await page.locator("input[name='name']").fill("SQA Inspect")
    await page.locator("input[name='expected_cycle_time_sec']").fill("75")
    await page.locator("input[name='erp_operation_number']").fill("0020")
    await page.locator("button[type='submit']").click()

    step_row = page.locator("tr").filter(has_text="SQA Inspect")
    await expect(step_row).to_be_visible(timeout=8_000)
    await expect(step_row.locator("td", has_text="20")).to_be_visible()

    list_resp = api.get(f"{API_ROUTES}/{route['id']}/process-segments", params={"limit": "200"})
    assert list_resp.status_code == 200, list_resp.text
    created = next((item for item in list_resp.json()["data"] if item["name"] == "SQA Inspect"), None)
    assert created is not None
    assert created["sequence"] == 20
    assert created["step_type"] == "inspection"
    assert created["expected_cycle_time_sec"] == 75
    assert created["erp_operation_number"] == "0020"

    await step_row.get_by_title("Edit step").click()
    await expect(page.get_by_role("heading", name="Edit Step")).to_be_visible(timeout=5_000)

    await page.locator("input[name='sequence']").fill("30")
    await page.locator("select[name='step_type']").select_option("rework")
    await page.locator("input[name='name']").fill("SQA Reinspect")
    await page.locator("input[name='expected_cycle_time_sec']").fill("95")
    await page.locator("input[name='erp_operation_number']").fill("0030")
    await page.locator("button[type='submit']").click()

    updated_row = page.locator("tr").filter(has_text="SQA Reinspect")
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.locator("td", has_text="30")).to_be_visible()

    detail_resp = api.get(f"/process-segments/{created['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    updated = detail_resp.json()["data"]
    assert updated["name"] == "SQA Reinspect"
    assert updated["sequence"] == 30
    assert updated["step_type"] == "rework"
    assert updated["expected_cycle_time_sec"] == 95
    assert updated["erp_operation_number"] == "0030"

    page.on("dialog", lambda dialog: dialog.accept())
    await updated_row.get_by_title("Delete step").click()

    await expect(page.get_by_text("SQA Reinspect")).to_be_hidden(timeout=8_000)

    delete_resp = api.get(f"/process-segments/{created['id']}")
    assert delete_resp.status_code == 404, (
        f"Expected 404 after delete, got {delete_resp.status_code}: {delete_resp.text}"
    )


@pytest.mark.ui
@pytest.mark.usefixtures("route_cleanup", "product_cleanup", "uom_cleanup")
async def test_route_product_assignment(page: Page, api) -> None:
    route = _create_route(api, name="SQA Product Assignment Route", version="4.0")
    uom = _create_scalar_uom(api, symbol=f"SQA_RT_{uuid4().hex[:8]}", name="SQA Route Assignment Each")
    product = _create_product(api, uom_id=uom["id"])

    await _open_routes_page(page)
    await _select_route(page, route_name=route["name"], route_version=route["version"])

    await page.get_by_role("button", name="Assign", exact=True).click()
    await page.locator("input[type='radio'][name='pickerSource']").nth(1).check()

    picker_item = page.locator("button").filter(has_text=product["code"]).filter(has_text=product["name"]).first
    await expect(picker_item).to_be_visible(timeout=8_000)
    await picker_item.click()

    product_row = page.locator("div").filter(has_text=product["code"]).filter(has_text=product["name"]).filter(has=page.get_by_title("Remove assignment")).first
    await expect(product_row).to_be_visible(timeout=8_000)

    assign_resp = api.get(f"{API_ROUTES}/{route['id']}/products", params={"limit": "200"})
    assert assign_resp.status_code == 200, assign_resp.text
    assignments = assign_resp.json()["data"]
    assert any(item["product_id"] == product["id"] for item in assignments)

    page.on("dialog", lambda dialog: dialog.accept())
    await product_row.get_by_title("Remove assignment").click()

    await expect(page.get_by_text(product["code"])).to_be_hidden(timeout=8_000)

    unassign_resp = api.get(f"{API_ROUTES}/{route['id']}/products", params={"limit": "200"})
    assert unassign_resp.status_code == 200, unassign_resp.text
    remaining = unassign_resp.json()["data"]
    assert all(item["product_id"] != product["id"] for item in remaining)


@pytest.mark.ui
@pytest.mark.usefixtures("route_cleanup", "material_cleanup", "uom_cleanup")
async def test_route_material_assignment(page: Page, api) -> None:
    route = _create_route(api, name="SQA Material Assignment Route", version="5.0")
    uom = _create_scalar_uom(api, symbol=f"SQA_RM_{uuid4().hex[:8]}", name="SQA Route Material Each")
    material = _create_material(api, uom_id=uom["id"])

    await _open_routes_page(page)
    await _select_route(page, route_name=route["name"], route_version=route["version"])

    await page.get_by_role("button", name="Assign", exact=True).click()

    picker_item = page.locator("button").filter(has_text=material["code"]).filter(has_text=material["name"]).first
    await expect(picker_item).to_be_visible(timeout=8_000)
    await picker_item.click()

    material_row = page.locator("div").filter(has_text=material["code"]).filter(has_text=material["name"]).filter(has=page.get_by_title("Remove assignment")).first
    await expect(material_row).to_be_visible(timeout=8_000)

    assign_resp = api.get(f"{API_ROUTES}/{route['id']}/materials", params={"limit": "200"})
    assert assign_resp.status_code == 200, assign_resp.text
    assignments = assign_resp.json()["data"]
    assert any(item["material_id"] == material["id"] for item in assignments)

    page.on("dialog", lambda dialog: dialog.accept())
    await material_row.get_by_title("Remove assignment").click()

    await expect(page.get_by_text(material["code"])).to_be_hidden(timeout=8_000)

    unassign_resp = api.get(f"{API_ROUTES}/{route['id']}/materials", params={"limit": "200"})
    assert unassign_resp.status_code == 200, unassign_resp.text
    remaining = unassign_resp.json()["data"]
    assert all(item["material_id"] != material["id"] for item in remaining)