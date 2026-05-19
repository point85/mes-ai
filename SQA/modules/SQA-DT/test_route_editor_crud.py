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
from playwright.async_api import Locator, Page, expect
from uuid import uuid4

import os
_DT_BASE = os.environ.get("SQA_DT_URL", "http://localhost:5177")
DT_DISPOSITIONS_URL = f"{_DT_BASE}/dispositions"
DT_ROUTES_URL = f"{_DT_BASE}/routes"
API_DISPOSITIONS = "/dispositions"
API_ROUTES = "/operations-definitions"
API_PRODUCTS = "/products"
API_MATERIALS = "/materials"
API_UOM = "/uom"
API_DATA_DEFINITIONS = "/data/definitions"
API_EQUIPMENT_CLASSES = "/equipment-classes"


async def _open_dispositions_page(page: Page) -> None:
    await page.goto(DT_DISPOSITIONS_URL)
    await expect(page.get_by_role("heading", name="Dispositions")).to_be_visible(timeout=10_000)


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


def _create_step(api, *, route_id: str, **overrides) -> dict:
    payload = {
        "sequence": 10,
        "name": "SQA Seeded Step",
        "step_type": "production",
        "work_cell_id": None,
        "equipment_class_id": None,
        "expected_cycle_time_sec": 60,
        "erp_operation_number": "0010",
        "is_initial_step": True,
        "input_disposition_ids": [],
        "output_disposition_ids": [],
    }
    payload.update(overrides)
    resp = api.post(f"{API_ROUTES}/{route_id}/process-segments", json=payload)
    assert resp.status_code in (200, 201), f"Step setup failed: {resp.text}"
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


def _assign_material_to_route(api, *, route_id: str, material_id: str) -> None:
    resp = api.post(f"{API_ROUTES}/{route_id}/materials", json={"material_id": material_id})
    assert resp.status_code in (200, 201), f"Route material assignment failed: {resp.text}"


def _create_data_definition(api, **overrides) -> dict:
    payload = {
        "code": f"SQA_DD_{uuid4().hex[:8]}",
        "name": "SQA Step Data Definition",
        "description": "SQA data definition for step binding tests",
        "data_type": "numeric",
        "source": "manual",
        "is_required": False,
        "lower_limit": 1,
        "upper_limit": 10,
        "step_id": None,
    }
    payload.update(overrides)
    resp = api.post(API_DATA_DEFINITIONS, json=payload)
    assert resp.status_code in (200, 201), f"Data definition setup failed: {resp.text}"
    return resp.json()["data"]


def _create_equipment_class(api, **overrides) -> dict:
    payload = {
        "name": "SQA Route Step Equipment Class",
        "code": f"SQA_EC_{uuid4().hex[:8]}",
        "description": "SQA equipment class for route-step requirement tests",
    }
    payload.update(overrides)
    resp = api.post(API_EQUIPMENT_CLASSES, json=payload)
    assert resp.status_code in (200, 201), f"Equipment class setup failed: {resp.text}"
    return resp.json()["data"]


def _create_disposition(api, **overrides) -> dict:
    payload = {
        "code": f"SQA_ROUTE_DISP_{uuid4().hex[:8]}",
        "name": "SQA Route Disposition",
        "description": "SQA disposition for route-step wiring tests",
        "category": "route",
    }
    payload.update(overrides)
    resp = api.post(API_DISPOSITIONS, json=payload)
    assert resp.status_code in (200, 201), f"Disposition setup failed: {resp.text}"
    return resp.json()["data"]


def _find_route_by_name(api, name: str):
    resp = api.get(API_ROUTES, params={"limit": "200"})
    assert resp.status_code == 200, f"List routes failed: {resp.text}"
    for item in resp.json().get("data", []):
        if item.get("name") == name:
            return item
    return None


def _find_disposition_by_code(api, code: str):
    resp = api.get(API_DISPOSITIONS, params={"limit": "200"})
    assert resp.status_code == 200, f"List dispositions failed: {resp.text}"
    for item in resp.json().get("data", []):
        if item.get("code") == code:
            return item
    return None


@pytest.fixture
def equipment_class_cleanup(api):
    yield

    resp = api.get(API_EQUIPMENT_CLASSES, params={"limit": "200"})
    assert resp.status_code == 200, f"Equipment class cleanup list failed: {resp.text}"
    for item in resp.json().get("data", []):
        code = item.get("code") or ""
        if not code.startswith("SQA_EC_"):
            continue
        delete_resp = api.delete(f"{API_EQUIPMENT_CLASSES}/{item['id']}")
        assert delete_resp.status_code in (200, 204, 404), (
            f"Equipment class cleanup delete failed for {code}: {delete_resp.status_code} {delete_resp.text}"
        )


@pytest.fixture
def disposition_cleanup(api):
    yield

    resp = api.get(API_DISPOSITIONS, params={"limit": "200"})
    assert resp.status_code == 200, f"Disposition cleanup list failed: {resp.text}"
    for item in resp.json().get("data", []):
        code = item.get("code") or ""
        if not code.startswith("SQA_ROUTE_DISP_"):
            continue
        delete_resp = api.delete(f"{API_DISPOSITIONS}/{item['id']}")
        assert delete_resp.status_code in (200, 204, 404), (
            f"Disposition cleanup delete failed for {code}: {delete_resp.status_code} {delete_resp.text}"
        )


async def _select_route(page: Page, *, route_name: str, route_version: str) -> None:
    select_button = page.locator("button").filter(has_text=route_name).filter(has_text=f"v{route_version}").first
    await expect(select_button).to_be_visible(timeout=8_000)
    await select_button.click()
    await expect(page.get_by_text(f"Steps — {route_name}")).to_be_visible(timeout=8_000)


def _route_entry(page: Page, *, route_name: str, route_version: str) -> Locator:
    select_button = page.locator("button").filter(has_text=route_name).filter(has_text=f"v{route_version}").first
    return select_button.locator("xpath=ancestor::div[contains(@class,'flex items-center justify-between')][1]")


def _step_row(page: Page, step_name: str) -> Locator:
    return page.locator("tr").filter(has_text=step_name)


async def _open_step_edit_dialog(page: Page, *, step_name: str) -> Locator:
    row = _step_row(page, step_name)
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Edit step").click()
    dialog = page.get_by_role("dialog")
    await expect(dialog.get_by_role("heading", name="Edit Step")).to_be_visible(timeout=5_000)
    return dialog


def _step_subeditor(dialog: Locator, title: str) -> Locator:
    return dialog.locator(
        f"xpath=.//h4[normalize-space()='{title}']/ancestor::div[contains(@class,'rounded-md')][1]"
    )


async def _wait_for_api_match(page: Page, fetcher, predicate, *, timeout_ms: int = 8_000):
    deadline = timeout_ms
    while deadline >= 0:
        payload = fetcher()
        if predicate(payload):
            return payload
        await page.wait_for_timeout(200)
        deadline -= 200
    return fetcher()


def _step_disposition_checkbox(dialog: Locator, *, section_title: str, code: str) -> Locator:
    disposition_list = dialog.locator(
        f"xpath=.//p[normalize-space()='{section_title}']/following-sibling::ul[1]"
    )
    return disposition_list.locator("li").filter(has_text=code).get_by_role("checkbox")


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

    route_entry = _route_entry(page, route_name=route_name, route_version="2.0")
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

    updated_entry = _route_entry(
        page,
        route_name="SQA Standalone Route Updated",
        route_version="2.1",
    )
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
@pytest.mark.usefixtures("route_cleanup", "disposition_cleanup")
async def test_route_step_disposition_wiring(page: Page, api) -> None:
    route = _create_route(api, name="SQA Disposition Wiring Route", version="6.0")
    input_a = _create_disposition(
        api,
        code=f"SQA_ROUTE_DISP_IN_{uuid4().hex[:6]}",
        name="SQA Input A",
    )
    output_a = _create_disposition(
        api,
        code=f"SQA_ROUTE_DISP_OUT_{uuid4().hex[:6]}",
        name="SQA Output A",
    )
    hold_disposition = _create_disposition(
        api,
        code=f"SQA_ROUTE_DISP_HOLD_{uuid4().hex[:6]}",
        name="SQA Hold",
        category="hold",
    )

    await _open_routes_page(page)
    await _select_route(page, route_name=route["name"], route_version=route["version"])

    await page.get_by_role("button", name="New Step").click()
    dialog = page.get_by_role("dialog")
    await expect(dialog.get_by_role("heading", name="New Step")).to_be_visible(timeout=5_000)

    await dialog.locator("input[name='sequence']").fill("40")
    await dialog.locator("select[name='step_type']").select_option("production")
    await dialog.locator("input[name='name']").fill("SQA Wired Step")
    await dialog.locator("input[name='expected_cycle_time_sec']").fill("60")
    await dialog.locator("input[name='erp_operation_number']").fill("0040")

    await expect(dialog.locator("li").filter(has_text=hold_disposition["code"])).to_have_count(0)

    await _step_disposition_checkbox(dialog, section_title="Input Dispositions", code=input_a["code"]).check()
    await _step_disposition_checkbox(dialog, section_title="Output Dispositions", code=output_a["code"]).check()
    await dialog.get_by_role("button", name="Create").click()
    await expect(dialog).to_be_hidden(timeout=8_000)

    step_row = page.locator("tr").filter(has_text="SQA Wired Step")
    await expect(step_row).to_be_visible(timeout=8_000)

    list_resp = api.get(f"{API_ROUTES}/{route['id']}/process-segments", params={"limit": "200"})
    assert list_resp.status_code == 200, list_resp.text
    created = next((item for item in list_resp.json()["data"] if item["name"] == "SQA Wired Step"), None)
    assert created is not None

    detail_resp = api.get(f"/process-segments/{created['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    created_detail = detail_resp.json()["data"]
    assert [item["code"] for item in created_detail["input_dispositions"]] == [input_a["code"]]
    assert [item["code"] for item in created_detail["output_dispositions"]] == [output_a["code"]]

    await step_row.get_by_title("Edit step").click()
    dialog = page.get_by_role("dialog")
    await expect(dialog.get_by_role("heading", name="Edit Step")).to_be_visible(timeout=5_000)
    await expect(
        _step_disposition_checkbox(dialog, section_title="Input Dispositions", code=input_a["code"])
    ).to_be_checked()
    await expect(
        _step_disposition_checkbox(dialog, section_title="Output Dispositions", code=output_a["code"])
    ).to_be_checked()
    await expect(dialog.locator("li").filter(has_text=hold_disposition["code"])).to_have_count(0)


@pytest.mark.ui
@pytest.mark.usefixtures("disposition_cleanup")
async def test_route_disposition_editor_crud(page: Page, api) -> None:
    disposition_code = f"SQA_ROUTE_DISP_{uuid4().hex[:8]}"

    await _open_dispositions_page(page)
    await page.get_by_role("button", name="New Disposition").click()
    await expect(page.get_by_role("heading", name="New Disposition")).to_be_visible(timeout=5_000)

    await page.locator("input[name='code']").fill(disposition_code)
    await page.locator("input[name='name']").fill("SQA Route Disposition")
    await page.locator("textarea[name='description']").fill("SQA route disposition create path")
    await page.locator("select[name='category']").select_option("route")
    await page.get_by_role("button", name="Create").click()

    disposition_row = page.locator("tr").filter(has_text=disposition_code)
    await expect(disposition_row).to_be_visible(timeout=8_000)
    await expect(disposition_row).to_contain_text("SQA Route Disposition")
    await expect(disposition_row.locator("span", has_text="route")).to_be_visible()

    created = _find_disposition_by_code(api, disposition_code)
    assert created is not None
    assert created["name"] == "SQA Route Disposition"
    assert created["description"] == "SQA route disposition create path"
    assert created["category"] == "route"

    await disposition_row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Disposition")).to_be_visible(timeout=5_000)

    await page.locator("input[name='name']").fill("SQA Route Disposition Updated")
    await page.locator("textarea[name='description']").fill("SQA route disposition edit path")
    await page.locator("select[name='category']").select_option("hold")
    await page.get_by_role("button", name="Save").click()

    updated_row = page.locator("tr").filter(has_text=disposition_code)
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row).to_contain_text("SQA Route Disposition Updated")
    await expect(updated_row.locator("span", has_text="hold")).to_be_visible()

    detail_resp = api.get(f"{API_DISPOSITIONS}/{created['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    updated = detail_resp.json()["data"]
    assert updated["code"] == disposition_code
    assert updated["name"] == "SQA Route Disposition Updated"
    assert updated["description"] == "SQA route disposition edit path"
    assert updated["category"] == "hold"

    page.on("dialog", lambda dialog: dialog.accept())
    await updated_row.get_by_title("Delete").click()

    await expect(page.locator("tr").filter(has_text=disposition_code)).to_have_count(0, timeout=8_000)

    delete_resp = api.get(f"{API_DISPOSITIONS}/{created['id']}")
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


@pytest.mark.ui
@pytest.mark.usefixtures("route_cleanup", "uom_cleanup")
async def test_route_step_parameter_editor(page: Page, api) -> None:
    route = _create_route(api, name="SQA Parameter Route", version="7.0")
    step = _create_step(api, route_id=route["id"], name="SQA Parameter Step")
    uom = _create_scalar_uom(api, symbol=f"SQA_P_{uuid4().hex[:8]}", name="SQA Parameter Count")

    await _open_routes_page(page)
    await _select_route(page, route_name=route["name"], route_version=route["version"])
    dialog = await _open_step_edit_dialog(page, step_name=step["name"])

    section = _step_subeditor(dialog, "Step Parameters")
    await section.get_by_placeholder("Torque, Temperature, Serial #, …").fill("SQA Torque")
    await section.locator("select").nth(0).select_option("numeric")
    await section.locator("select").nth(1).select_option(value=uom["id"])
    await section.get_by_placeholder("setpoint").fill("5.5")
    await section.get_by_role("button", name="Add").click()

    parameter_row = section.locator("li").filter(has_text="SQA Torque")
    await expect(parameter_row).to_be_visible(timeout=8_000)
    await expect(parameter_row).to_contain_text("5.5")

    list_resp = api.get(f"/process-segments/{step['id']}/parameters", params={"limit": "200"})
    assert list_resp.status_code == 200, list_resp.text
    created = next((item for item in list_resp.json()["data"] if item["name"] == "SQA Torque"), None)
    assert created is not None
    assert created["data_type"] == "numeric"
    assert created["uom_id"] == uom["id"]
    assert created["target_value"] == "5.5"

    page.once("dialog", lambda dialog_handle: dialog_handle.accept())
    await parameter_row.get_by_label("Remove parameter").click()
    await expect(section.locator("li").filter(has_text="SQA Torque")).to_have_count(0, timeout=8_000)

    delete_resp = api.get(f"/process-segments/{step['id']}/parameters", params={"limit": "200"})
    assert delete_resp.status_code == 200, delete_resp.text
    assert all(item["id"] != created["id"] for item in delete_resp.json()["data"])


@pytest.mark.ui
@pytest.mark.usefixtures("route_cleanup", "data_definition_cleanup")
async def test_route_step_data_definition_editor(page: Page, api) -> None:
    route = _create_route(api, name="SQA Data Definition Route", version="7.1")
    step = _create_step(api, route_id=route["id"], name="SQA Data Definition Step")
    definition = _create_data_definition(api, name="SQA Bound Definition")

    await _open_routes_page(page)
    await _select_route(page, route_name=route["name"], route_version=route["version"])
    dialog = await _open_step_edit_dialog(page, step_name=step["name"])

    section = _step_subeditor(dialog, "Data Definitions")
    await section.locator("select").select_option(value=definition["id"])
    await section.get_by_role("button", name="Attach").click()

    definition_row = section.locator("li").filter(has_text=definition["code"])
    await expect(definition_row).to_be_visible(timeout=8_000)

    detail_resp = api.get(f"{API_DATA_DEFINITIONS}/{definition['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    attached = detail_resp.json()["data"]
    assert attached["step_id"] == step["id"]

    page.once("dialog", lambda dialog_handle: dialog_handle.accept())
    await definition_row.get_by_label("Detach data definition").click()
    await expect(section.locator("li").filter(has_text=definition["code"])).to_have_count(0, timeout=8_000)

    detached_resp = api.get(f"{API_DATA_DEFINITIONS}/{definition['id']}")
    assert detached_resp.status_code == 200, detached_resp.text
    detached = detached_resp.json()["data"]
    assert detached["step_id"] is None


@pytest.mark.ui
@pytest.mark.usefixtures("route_cleanup", "equipment_class_cleanup")
async def test_route_step_equipment_requirements_editor(page: Page, api) -> None:
    route = _create_route(api, name="SQA Equipment Requirement Route", version="7.2")
    step = _create_step(api, route_id=route["id"], name="SQA Equipment Requirement Step")
    equipment_class = _create_equipment_class(api)

    await _open_routes_page(page)
    await _select_route(page, route_name=route["name"], route_version=route["version"])
    dialog = await _open_step_edit_dialog(page, step_name=step["name"])

    section = _step_subeditor(dialog, "Equipment Requirements")
    await section.get_by_label("Requirement equipment class").select_option(value=equipment_class["id"])
    await section.get_by_label("Requirement use type").select_option("required")
    await section.get_by_role("button", name="Add").click()

    requirement_row = section.locator("li").filter(has_text=equipment_class["code"])
    await expect(requirement_row).to_be_visible(timeout=8_000)
    await requirement_row.locator("select").select_option("preferred")
    await expect(requirement_row).to_contain_text("preferred", timeout=8_000)

    list_resp = await _wait_for_api_match(
        page,
        lambda: api.get(f"/process-segments/{step['id']}/equipment-requirements"),
        lambda resp: resp.status_code == 200 and any(
            item["equipment_class_id"] == equipment_class["id"] and item["use_type"] == "preferred"
            for item in resp.json()["data"]
        ),
    )
    assert list_resp.status_code == 200, list_resp.text
    created = next((item for item in list_resp.json()["data"] if item["equipment_class_id"] == equipment_class["id"]), None)
    assert created is not None
    assert created["use_type"] == "preferred"

    await requirement_row.get_by_label("Remove requirement").click()
    await expect(section.locator("li").filter(has_text=equipment_class["code"])).to_have_count(0, timeout=8_000)

    delete_resp = api.get(f"/process-segments/{step['id']}/equipment-requirements")
    assert delete_resp.status_code == 200, delete_resp.text
    assert all(item["id"] != created["id"] for item in delete_resp.json()["data"])


@pytest.mark.ui
@pytest.mark.usefixtures("route_cleanup", "material_cleanup", "uom_cleanup")
async def test_route_step_material_requirements_editor(page: Page, api) -> None:
    route = _create_route(api, name="SQA Material Requirement Route", version="7.3")
    step = _create_step(api, route_id=route["id"], name="SQA Material Requirement Step")
    uom = _create_scalar_uom(api, symbol=f"SQA_SM_{uuid4().hex[:8]}", name="SQA Step Material Each")
    material = _create_material(api, uom_id=uom["id"], name="SQA Step Material")
    # The MaterialRequirementsEditor dropdown only lists materials assigned to the route.
    _assign_material_to_route(api, route_id=route["id"], material_id=material["id"])

    await _open_routes_page(page)
    await _select_route(page, route_name=route["name"], route_version=route["version"])
    dialog = await _open_step_edit_dialog(page, step_name=step["name"])

    section = _step_subeditor(dialog, "Material Requirements")
    await section.locator("select").nth(0).select_option(value=material["id"])
    await section.locator("input[type='number']").nth(0).fill("2.5")
    await section.locator("select").nth(1).select_option(value=uom["id"])
    await section.locator("select").nth(2).select_option("consumed")
    await section.get_by_role("button", name="Add").click()

    list_resp = await _wait_for_api_match(
        page,
        lambda: api.get(f"/process-segments/{step['id']}/material-requirements"),
        lambda resp: resp.status_code == 200 and any(
            item["material_id"] == material["id"]
            for item in resp.json()["data"]
        ),
    )
    assert list_resp.status_code == 200, list_resp.text
    created = next((item for item in list_resp.json()["data"] if item["material_id"] == material["id"]), None)
    assert created is not None
    assert created["quantity"] == 2.5
    assert created["material_use"] == "consumed"
    assert created["position"] == 0
