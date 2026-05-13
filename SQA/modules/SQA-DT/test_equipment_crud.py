"""
SQA-DT -- Equipment editor CRUD tests.

Surfaces:
- DT-CLIENT /work-cells/:wcId/equipment page
- DT-CLIENT /equipment/{equipId}/capabilities page
- MES REST API /api/v1/work-cells/{wcId}/equipment
- MES REST API /api/v1/equipment/{equipId}
- MES REST API /api/v1/equipment/{equipId}/capabilities
- MES REST API /api/v1/equipment-capabilities/{capId}
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from playwright.async_api import Page, expect

API_SITES = "/sites"
API_UOM = "/uom"
API_MATERIALS = "/materials"
API_EQUIPMENT_CLASSES = "/equipment-classes"


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


def _create_rate_uom(api, *, symbol: str, name: str, left_uom_symbol: str, right_uom_symbol: str) -> dict:
    resp = api.post(
        API_UOM,
        json={
            "symbol": symbol,
            "name": name,
            "uom_type": "count",
            "uom_class": "quotient",
            "multiplier": 1.0,
            "offset": 0.0,
            "left_uom_symbol": left_uom_symbol,
            "right_uom_symbol": right_uom_symbol,
        },
    )
    assert resp.status_code in (200, 201), f"Rate UoM setup failed: {resp.text}"
    return resp.json()["data"]


def _create_material(api, *, uom_id: str, **overrides) -> dict:
    payload = {
        "code": _unique_code("SQA_MAT"),
        "name": "SQA Equipment Material",
        "description": "SQA material for equipment material setup tests",
        "material_type": "raw",
        "uom_id": uom_id,
    }
    payload.update(overrides)
    resp = api.post(API_MATERIALS, json=payload)
    assert resp.status_code in (200, 201), f"Material setup failed: {resp.text}"
    return resp.json()["data"]


def _create_equipment_class(api, **overrides) -> dict:
    payload = {
        "name": "SQA Equipment Class",
        "code": _unique_code("SQA_EC"),
        "description": "SQA equipment class",
    }
    payload.update(overrides)
    resp = api.post(API_EQUIPMENT_CLASSES, json=payload)
    assert resp.status_code in (200, 201), f"Equipment class setup failed: {resp.text}"
    return resp.json()["data"]


def _create_site(api) -> dict:
    resp = api.post(
        API_SITES,
        json={
            "name": "SQA Equipment Site",
            "code": _unique_code("SQA_ST"),
            "description": "SQA site for equipment tests",
        },
    )
    assert resp.status_code in (200, 201), f"Site setup failed: {resp.text}"
    return resp.json()["data"]


def _create_area(api, *, site_id: str) -> dict:
    resp = api.post(
        f"{API_SITES}/{site_id}/areas",
        json={
            "name": "SQA Equipment Area",
            "code": _unique_code("SQA_AR"),
            "description": "SQA area for equipment tests",
        },
    )
    assert resp.status_code in (200, 201), f"Area setup failed: {resp.text}"
    return resp.json()["data"]


def _create_line(api, *, area_id: str) -> dict:
    resp = api.post(
        f"/areas/{area_id}/lines",
        json={
            "name": "SQA Equipment Line",
            "code": _unique_code("SQA_LN"),
            "description": "SQA line for equipment tests",
        },
    )
    assert resp.status_code in (200, 201), f"Line setup failed: {resp.text}"
    return resp.json()["data"]


def _create_work_cell(api, *, line_id: str) -> dict:
    resp = api.post(
        f"/lines/{line_id}/work-cells",
        json={
            "name": "SQA Equipment Work Cell",
            "code": _unique_code("SQA_WC"),
            "description": "SQA work cell for equipment tests",
        },
    )
    assert resp.status_code in (200, 201), f"Work cell setup failed: {resp.text}"
    return resp.json()["data"]


def _create_equipment(api, *, wc_id: str, **overrides) -> dict:
    payload = {
        "name": "SQA Equipment",
        "code": _unique_code("SQA_EQ"),
        "description": "SQA equipment",
        "max_queue_depth": 5,
    }
    payload.update(overrides)
    resp = api.post(f"/work-cells/{wc_id}/equipment", json=payload)
    assert resp.status_code in (200, 201), f"Equipment setup failed: {resp.text}"
    return resp.json()["data"]


def _create_equipment_material(api, *, equip_id: str, material_id: str, design_speed_uom_id: str, reject_uom_id: str, **overrides) -> dict:
    payload = {
        "material_id": material_id,
        "design_speed": 120.0,
        "design_speed_uom_id": design_speed_uom_id,
        "reject_uom_id": reject_uom_id,
        "target_oee": 88.5,
    }
    payload.update(overrides)
    resp = api.post(f"/equipment/{equip_id}/materials", json=payload)
    assert resp.status_code in (200, 201), f"Equipment material setup failed: {resp.text}"
    return resp.json()["data"]


async def _open_equipment_page(page: Page, *, wc_id: str) -> None:
    await page.goto(f"http://localhost:5177/work-cells/{wc_id}/equipment")
    await expect(page.get_by_role("heading", name="Equipment")).to_be_visible(timeout=10_000)


async def _open_equipment_class_page(page: Page) -> None:
    await page.goto("http://localhost:5177/equipment-classes")
    await expect(page.get_by_role("heading", name="Equipment Classes")).to_be_visible(timeout=10_000)


async def _open_capability_page(page: Page, *, wc_id: str, equipment_code: str) -> None:
    await _open_equipment_page(page, wc_id=wc_id)
    row = page.locator("tr").filter(has_text=equipment_code)
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Capabilities").click()
    await expect(page.get_by_role("heading", name="Equipment Capabilities")).to_be_visible(timeout=10_000)


async def _open_material_page(page: Page, *, wc_id: str, equipment_code: str) -> None:
    await _open_equipment_page(page, wc_id=wc_id)
    row = page.locator("tr").filter(has_text=equipment_code)
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Material Setups").click()
    await expect(page.get_by_role("heading", name="Material Setups")).to_be_visible(timeout=10_000)


def _create_hierarchy(api) -> dict:
    site = _create_site(api)
    area = _create_area(api, site_id=site["id"])
    line = _create_line(api, area_id=area["id"])
    work_cell = _create_work_cell(api, line_id=line["id"])
    return {
        "site": site,
        "area": area,
        "line": line,
        "work_cell": work_cell,
    }


@pytest.fixture(autouse=False)
def equipment_class_cleanup(api):
    def _delete_sqa_equipment_classes() -> None:
        resp = api.get(API_EQUIPMENT_CLASSES, params={"limit": "200"})
        if resp.status_code != 200:
            return
        for equipment_class in resp.json().get("data", []):
            if equipment_class.get("code", "").startswith("SQA_EC_"):
                api.delete(f"{API_EQUIPMENT_CLASSES}/{equipment_class['id']}")

    _delete_sqa_equipment_classes()
    yield
    _delete_sqa_equipment_classes()


@pytest.mark.ui
@pytest.mark.usefixtures("equipment_class_cleanup")
async def test_equipment_class_crud(page: Page, api) -> None:
    code = _unique_code("SQA_EC")

    await _open_equipment_class_page(page)
    await page.get_by_role("button", name="New Class").click()
    await expect(page.get_by_role("heading", name="New Equipment Class")).to_be_visible(timeout=5_000)

    await page.locator("input").nth(0).fill("SQA Mixer Class")
    await page.locator("input").nth(1).fill(code)
    await page.locator("textarea").fill("SQA class create path")
    await page.get_by_role("button", name="Create").click()

    row = page.locator("tr").filter(has_text=code)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text="SQA Mixer Class")).to_be_visible()

    create_resp = api.get(API_EQUIPMENT_CLASSES, params={"limit": "200"})
    assert create_resp.status_code == 200, create_resp.text
    created = next((item for item in create_resp.json()["data"] if item["code"] == code), None)
    assert created is not None
    assert created["name"] == "SQA Mixer Class"
    assert created["description"] == "SQA class create path"

    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Equipment Class")).to_be_visible(timeout=5_000)

    await page.locator("input").nth(0).fill("SQA Oven Class")
    await page.locator("textarea").fill("SQA class edit path")
    await page.get_by_role("button", name="Save").click()

    updated_row = page.locator("tr").filter(has_text=code)
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.locator("td", has_text="SQA Oven Class")).to_be_visible()

    detail_resp = api.get(f"{API_EQUIPMENT_CLASSES}/{created['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    updated = detail_resp.json()["data"]
    assert updated["name"] == "SQA Oven Class"
    assert updated["description"] == "SQA class edit path"

    page.on("dialog", lambda dialog: dialog.accept())
    await updated_row.get_by_title("Delete").click()

    await expect(page.locator("td", has_text=code)).to_be_hidden(timeout=8_000)

    delete_resp = api.get(f"{API_EQUIPMENT_CLASSES}/{created['id']}")
    assert delete_resp.status_code == 404, (
        f"Expected 404 after delete, got {delete_resp.status_code}: {delete_resp.text}"
    )


@pytest.mark.ui
@pytest.mark.usefixtures("physical_model_cleanup")
async def test_equipment_create(page: Page, api) -> None:
    hierarchy = _create_hierarchy(api)
    wc_id = hierarchy["work_cell"]["id"]
    code = _unique_code("SQA_EQ")
    name = "SQA Filler 1"

    await _open_equipment_page(page, wc_id=wc_id)
    await page.get_by_role("button", name="New Equipment").click()
    await expect(page.get_by_role("heading", name="New Equipment")).to_be_visible(timeout=5_000)

    await page.locator("input[name='code']").fill(code)
    await page.locator("input[name='name']").fill(name)
    await page.locator("input[name='max_queue_depth']").fill("7")
    await page.locator("textarea[name='description']").fill("SQA create equipment path")
    await page.locator("button[type='submit']").click()

    row = page.locator("tr").filter(has_text=code)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text=name)).to_be_visible()

    resp = api.get(f"/work-cells/{wc_id}/equipment", params={"limit": "200"})
    assert resp.status_code == 200, resp.text
    created = next((item for item in resp.json()["data"] if item["code"] == code), None)
    assert created is not None
    assert created["name"] == name
    assert created["max_queue_depth"] == 7


@pytest.mark.ui
@pytest.mark.usefixtures("physical_model_cleanup")
async def test_equipment_search_filters_by_code_and_name(page: Page, api) -> None:
    hierarchy = _create_hierarchy(api)
    wc_id = hierarchy["work_cell"]["id"]
    match_equipment = _create_equipment(api, wc_id=wc_id, name="SQA Search Target")
    other_equipment = _create_equipment(api, wc_id=wc_id, name="SQA Search Other")

    await _open_equipment_page(page, wc_id=wc_id)

    search_box = page.locator("input[placeholder*='Search by name or code']")
    await search_box.fill(match_equipment["code"])
    await expect(page.locator("tr").filter(has_text=match_equipment["code"])).to_be_visible(timeout=8_000)
    await expect(page.locator("tr").filter(has_text=other_equipment["code"])).to_have_count(0)

    await search_box.fill("SQA Search Other")
    await expect(page.locator("tr").filter(has_text=other_equipment["code"])).to_be_visible(timeout=8_000)
    await expect(page.locator("tr").filter(has_text=match_equipment["code"])).to_have_count(0)

    await expect(page.get_by_text("1 item")).to_be_visible()
    await search_box.fill("")
    await expect(page.get_by_text("2 items")).to_be_visible(timeout=8_000)


@pytest.mark.ui
@pytest.mark.usefixtures("physical_model_cleanup")
async def test_equipment_edit(page: Page, api) -> None:
    hierarchy = _create_hierarchy(api)
    wc_id = hierarchy["work_cell"]["id"]
    equipment = _create_equipment(
        api,
        wc_id=wc_id,
        name="SQA Mixer 1",
        description="SQA original equipment",
        max_queue_depth=4,
    )

    await _open_equipment_page(page, wc_id=wc_id)

    row = page.locator("tr").filter(has_text=equipment["code"])
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Equipment")).to_be_visible(timeout=5_000)

    await page.locator("input[name='name']").fill("SQA Mixer 2")
    await page.locator("input[name='max_queue_depth']").fill("9")
    await page.locator("textarea[name='description']").fill("SQA edited equipment")
    await page.locator("button[type='submit']").click()

    updated_row = page.locator("tr").filter(has_text=equipment["code"])
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.locator("td", has_text="SQA Mixer 2")).to_be_visible()

    resp = api.get(f"/equipment/{equipment['id']}")
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]
    assert updated["name"] == "SQA Mixer 2"
    assert updated["max_queue_depth"] == 9
    assert updated["description"] == "SQA edited equipment"


@pytest.mark.ui
@pytest.mark.usefixtures("physical_model_cleanup")
async def test_equipment_delete(page: Page, api) -> None:
    hierarchy = _create_hierarchy(api)
    wc_id = hierarchy["work_cell"]["id"]
    equipment = _create_equipment(api, wc_id=wc_id, name="SQA Delete Equipment")

    await _open_equipment_page(page, wc_id=wc_id)

    row = page.locator("tr").filter(has_text=equipment["code"])
    await expect(row).to_be_visible(timeout=8_000)

    page.on("dialog", lambda dialog: dialog.accept())
    await row.get_by_title("Delete").click()

    await expect(page.locator("td", has_text=equipment["code"])).to_be_hidden(timeout=8_000)

    resp = api.get(f"/equipment/{equipment['id']}")
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}: {resp.text}"


@pytest.mark.ui
@pytest.mark.usefixtures("physical_model_cleanup")
async def test_equipment_capability_crud(page: Page, api) -> None:
    hierarchy = _create_hierarchy(api)
    wc_id = hierarchy["work_cell"]["id"]
    equipment = _create_equipment(api, wc_id=wc_id, name="SQA Capability Equipment")

    await _open_capability_page(page, wc_id=wc_id, equipment_code=equipment["code"])
    await page.get_by_role("button", name="Add Capability").click()
    await expect(page.get_by_role("heading", name="New Capability")).to_be_visible(timeout=5_000)

    await page.locator("select").nth(1).select_option("available")
    await page.locator("input[placeholder='e.g. Scheduled maintenance']").fill("SQA capability created")
    await page.get_by_role("button", name="Create").click()

    await expect(page.get_by_text("Reason: SQA capability created")).to_be_visible(timeout=8_000)
    create_resp = api.get(f"/equipment/{equipment['id']}/capabilities")
    assert create_resp.status_code == 200, create_resp.text
    created_caps = create_resp.json()["data"]
    assert len(created_caps) == 1
    capability = created_caps[0]
    assert capability["capability_type"] == "available"
    assert capability["reason"] == "SQA capability created"

    await page.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Capability")).to_be_visible(timeout=5_000)
    await page.locator("select").nth(1).select_option("committed")
    await page.locator("input[placeholder='e.g. Scheduled maintenance']").fill("SQA capability updated")
    await page.get_by_role("button", name="Save").click()

    await expect(page.get_by_text("Reason: SQA capability updated")).to_be_visible(timeout=8_000)
    await expect(page.get_by_text("committed")).to_be_visible()

    update_resp = api.get(f"/equipment/{equipment['id']}/capabilities")
    assert update_resp.status_code == 200, update_resp.text
    updated_caps = update_resp.json()["data"]
    assert len(updated_caps) == 1
    assert updated_caps[0]["id"] == capability["id"]
    assert updated_caps[0]["capability_type"] == "committed"
    assert updated_caps[0]["reason"] == "SQA capability updated"

    page.on("dialog", lambda dialog: dialog.accept())
    await page.get_by_title("Delete").click()

    await expect(page.get_by_text('No capabilities declared. Click "Add Capability" to define one.')).to_be_visible(timeout=8_000)

    delete_resp = api.get(f"/equipment/{equipment['id']}/capabilities")
    assert delete_resp.status_code == 200, delete_resp.text
    assert delete_resp.json()["data"] == []


@pytest.mark.ui
@pytest.mark.usefixtures("physical_model_cleanup", "uom_cleanup", "material_cleanup")
async def test_equipment_material_setup_create(page: Page, api) -> None:
    hierarchy = _create_hierarchy(api)
    wc_id = hierarchy["work_cell"]["id"]
    equipment = _create_equipment(api, wc_id=wc_id, name="SQA Material Create Equipment")
    material_uom = _create_scalar_uom(api, symbol=_unique_code("SQA_MU"), name="SQA Material UoM")
    time_uom = _create_scalar_uom(api, symbol=_unique_code("SQA_HR"), name="SQA Hour", uom_type="time", multiplier=3600.0)
    reject_uom = _create_scalar_uom(api, symbol=_unique_code("SQA_RJ"), name="SQA Reject UoM")
    speed_uom = _create_rate_uom(
        api,
        symbol=_unique_code("SQA_RT"),
        name="SQA Rate UoM",
        left_uom_symbol=reject_uom["symbol"],
        right_uom_symbol=time_uom["symbol"],
    )
    material = _create_material(api, uom_id=material_uom["id"], name="SQA Material Create")

    await _open_material_page(page, wc_id=wc_id, equipment_code=equipment["code"])
    await page.get_by_role("button", name="Add Material Setup").click()
    await expect(page.get_by_role("heading", name="New Material Setup")).to_be_visible(timeout=5_000)

    await page.locator("select[name='material_id']").select_option(material["id"])
    await page.locator("input[name='design_speed']").fill("144.5")
    await page.locator("select[name='design_speed_uom_id']").select_option(speed_uom["id"])
    await page.locator("select[name='reject_uom_id']").select_option(reject_uom["id"])
    await page.locator("input[name='target_oee']").fill("92.5")
    await page.get_by_role("button", name="Create").click()

    row = page.locator("tr").filter(has_text=material["code"])
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text="144.5")).to_be_visible()
    await expect(row.locator("td", has_text="92.5%")).to_be_visible()

    resp = api.get(f"/equipment/{equipment['id']}/materials", params={"limit": "200"})
    assert resp.status_code == 200, resp.text
    created = next((item for item in resp.json()["data"] if item["material_id"] == material["id"]), None)
    assert created is not None
    assert created["design_speed"] == 144.5
    assert created["design_speed_uom_id"] == speed_uom["id"]
    assert created["reject_uom_id"] == reject_uom["id"]
    assert created["target_oee"] == 92.5


@pytest.mark.ui
@pytest.mark.usefixtures("physical_model_cleanup", "uom_cleanup", "material_cleanup")
async def test_equipment_material_setup_edit(page: Page, api) -> None:
    hierarchy = _create_hierarchy(api)
    wc_id = hierarchy["work_cell"]["id"]
    equipment = _create_equipment(api, wc_id=wc_id, name="SQA Material Edit Equipment")
    material_uom = _create_scalar_uom(api, symbol=_unique_code("SQA_MU"), name="SQA Material UoM")
    time_uom = _create_scalar_uom(api, symbol=_unique_code("SQA_HR"), name="SQA Hour", uom_type="time", multiplier=3600.0)
    reject_uom = _create_scalar_uom(api, symbol=_unique_code("SQA_RJ"), name="SQA Reject UoM")
    updated_reject_uom = _create_scalar_uom(api, symbol=_unique_code("SQA_R2J"), name="SQA Updated Reject UoM")
    speed_uom = _create_rate_uom(
        api,
        symbol=_unique_code("SQA_RT"),
        name="SQA Rate UoM",
        left_uom_symbol=reject_uom["symbol"],
        right_uom_symbol=time_uom["symbol"],
    )
    updated_speed_uom = _create_rate_uom(
        api,
        symbol=_unique_code("SQA_R2"),
        name="SQA Updated Rate UoM",
        left_uom_symbol=updated_reject_uom["symbol"],
        right_uom_symbol=time_uom["symbol"],
    )
    material = _create_material(api, uom_id=material_uom["id"], name="SQA Material Edit")
    material_setup = _create_equipment_material(
        api,
        equip_id=equipment["id"],
        material_id=material["id"],
        design_speed_uom_id=speed_uom["id"],
        reject_uom_id=reject_uom["id"],
        design_speed=120.0,
        target_oee=81.0,
    )

    await _open_material_page(page, wc_id=wc_id, equipment_code=equipment["code"])
    row = page.locator("tr").filter(has_text=material["code"])
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Material Setup")).to_be_visible(timeout=5_000)

    await page.locator("input[name='design_speed']").fill("175")
    await page.locator("select[name='design_speed_uom_id']").select_option(updated_speed_uom["id"])
    await page.locator("select[name='reject_uom_id']").select_option(updated_reject_uom["id"])
    await page.locator("input[name='target_oee']").fill("96.2")
    await page.get_by_role("button", name="Update").click()

    updated_row = page.locator("tr").filter(has_text=material["code"])
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.locator("td", has_text="175")).to_be_visible()
    await expect(updated_row.locator("td", has_text="96.2%")).to_be_visible()

    resp = api.get(f"/equipment-materials/{material_setup['id']}")
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]
    assert updated["design_speed"] == 175
    assert updated["design_speed_uom_id"] == updated_speed_uom["id"]
    assert updated["reject_uom_id"] == updated_reject_uom["id"]
    assert updated["target_oee"] == 96.2


@pytest.mark.ui
@pytest.mark.usefixtures("physical_model_cleanup", "uom_cleanup", "material_cleanup")
async def test_equipment_material_setup_delete(page: Page, api) -> None:
    hierarchy = _create_hierarchy(api)
    wc_id = hierarchy["work_cell"]["id"]
    equipment = _create_equipment(api, wc_id=wc_id, name="SQA Material Delete Equipment")
    material_uom = _create_scalar_uom(api, symbol=_unique_code("SQA_MU"), name="SQA Material UoM")
    time_uom = _create_scalar_uom(api, symbol=_unique_code("SQA_HR"), name="SQA Hour", uom_type="time", multiplier=3600.0)
    reject_uom = _create_scalar_uom(api, symbol=_unique_code("SQA_RJ"), name="SQA Reject UoM")
    speed_uom = _create_rate_uom(
        api,
        symbol=_unique_code("SQA_RT"),
        name="SQA Rate UoM",
        left_uom_symbol=reject_uom["symbol"],
        right_uom_symbol=time_uom["symbol"],
    )
    material = _create_material(api, uom_id=material_uom["id"], name="SQA Material Delete")
    material_setup = _create_equipment_material(
        api,
        equip_id=equipment["id"],
        material_id=material["id"],
        design_speed_uom_id=speed_uom["id"],
        reject_uom_id=reject_uom["id"],
    )

    await _open_material_page(page, wc_id=wc_id, equipment_code=equipment["code"])
    row = page.locator("tr").filter(has_text=material["code"])
    await expect(row).to_be_visible(timeout=8_000)

    page.on("dialog", lambda dialog: dialog.accept())
    await row.get_by_title("Delete").click()

    await expect(page.locator("td", has_text=material["code"])).to_be_hidden(timeout=8_000)

    resp = api.get(f"/equipment-materials/{material_setup['id']}")
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}: {resp.text}"