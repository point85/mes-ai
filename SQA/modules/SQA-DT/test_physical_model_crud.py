"""
SQA-DT -- Physical model hierarchy CRUD tests.

Surfaces:
- DT-CLIENT /sites page
- DT-CLIENT /sites/{siteId}/areas page
- DT-CLIENT /areas/{areaId}/lines page
- DT-CLIENT /lines/{lineId}/work-cells page
- MES REST API /api/v1/sites
- MES REST API /api/v1/sites/{siteId}/areas
- MES REST API /api/v1/areas/{areaId}/lines
- MES REST API /api/v1/lines/{lineId}/work-cells
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from playwright.async_api import Page, expect

import os
_DT_BASE = os.environ.get("SQA_DT_URL", "http://localhost:5177")
DT_SITES_URL = f"{_DT_BASE}/sites"
API_SITES = "/sites"


def _unique_code(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _create_site(api, **overrides) -> dict:
    payload = {
        "name": "SQA Physical Site",
        "code": _unique_code("SQA_ST"),
        "description": "SQA site seed",
        "timezone": "America/Los_Angeles",
        "address": "100 SQA Plant Way",
    }
    payload.update(overrides)
    resp = api.post(API_SITES, json=payload)
    assert resp.status_code in (200, 201), f"Site setup failed: {resp.text}"
    return resp.json()["data"]


def _create_area(api, *, site_id: str, **overrides) -> dict:
    payload = {
        "name": "SQA Physical Area",
        "code": _unique_code("SQA_AR"),
        "description": "SQA area seed",
    }
    payload.update(overrides)
    resp = api.post(f"{API_SITES}/{site_id}/areas", json=payload)
    assert resp.status_code in (200, 201), f"Area setup failed: {resp.text}"
    return resp.json()["data"]


def _create_line(api, *, area_id: str, **overrides) -> dict:
    payload = {
        "name": "SQA Physical Line",
        "code": _unique_code("SQA_LN"),
        "description": "SQA line seed",
    }
    payload.update(overrides)
    resp = api.post(f"/areas/{area_id}/lines", json=payload)
    assert resp.status_code in (200, 201), f"Line setup failed: {resp.text}"
    return resp.json()["data"]


def _create_work_cell(api, *, line_id: str, **overrides) -> dict:
    payload = {
        "name": "SQA Physical Work Cell",
        "code": _unique_code("SQA_WC"),
        "description": "SQA work cell seed",
        "default_dispatch_strategy": "manual",
    }
    payload.update(overrides)
    resp = api.post(f"/lines/{line_id}/work-cells", json=payload)
    assert resp.status_code in (200, 201), f"Work cell setup failed: {resp.text}"
    return resp.json()["data"]


async def _open_sites_page(page: Page) -> None:
    await page.goto(DT_SITES_URL)
    await expect(page.get_by_role("heading", name="Sites")).to_be_visible(timeout=10_000)


async def _open_areas_page(page: Page, *, site_id: str, site_name: str) -> None:
    await page.goto(f"{_DT_BASE}/sites/{site_id}/areas", wait_until="networkidle")
    await expect(page.get_by_role("heading", name="Areas")).to_be_visible(timeout=10_000)
    await expect(page.get_by_text(f"Areas within {site_name}.")).to_be_visible(timeout=10_000)


async def _open_lines_page(page: Page, *, area_id: str, area_name: str) -> None:
    await page.goto(f"{_DT_BASE}/areas/{area_id}/lines", wait_until="networkidle")
    await expect(page.get_by_role("heading", name="Production Lines")).to_be_visible(timeout=10_000)
    await expect(page.get_by_text(f"Lines within area {area_name}.")).to_be_visible(timeout=10_000)


async def _open_work_cells_page(page: Page, *, line_id: str, line_name: str) -> None:
    await page.goto(f"{_DT_BASE}/lines/{line_id}/work-cells", wait_until="networkidle")
    await expect(page.get_by_role("heading", name="Work Cells")).to_be_visible(timeout=10_000)
    await expect(page.get_by_text(f"Work cells on line {line_name}.")).to_be_visible(timeout=10_000)


@pytest.mark.ui
@pytest.mark.usefixtures("physical_model_cleanup")
async def test_site_crud(page: Page, api) -> None:
    code = _unique_code("SQA_ST")

    await _open_sites_page(page)
    await page.get_by_role("button", name="New Site").click()
    await expect(page.get_by_role("heading", name="New Site")).to_be_visible(timeout=5_000)

    await page.locator("input[name='code']").fill(code)
    await page.locator("input[name='name']").fill("SQA Primary Site")
    await page.locator("input[name='address']").fill("200 SQA Site Road")
    await page.locator("textarea[name='description']").fill("SQA site create path")
    await page.locator("button[type='submit']").click()

    row = page.locator("tr").filter(has_text=code)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text="SQA Primary Site")).to_be_visible()

    list_resp = api.get(API_SITES, params={"limit": "200"})
    assert list_resp.status_code == 200, list_resp.text
    created = next((item for item in list_resp.json()["data"] if item["code"] == code), None)
    assert created is not None
    assert created["name"] == "SQA Primary Site"
    assert created["address"] == "200 SQA Site Road"
    assert created["description"] == "SQA site create path"

    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Site")).to_be_visible(timeout=5_000)

    await page.locator("input[name='name']").fill("SQA Primary Site Updated")
    await page.locator("input[name='address']").fill("300 SQA Site Road")
    await page.locator("textarea[name='description']").fill("SQA site edit path")
    await page.locator("button[type='submit']").click()

    updated_row = page.locator("tr").filter(has_text=code)
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.locator("td", has_text="SQA Primary Site Updated")).to_be_visible()

    detail_resp = api.get(f"{API_SITES}/{created['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    updated = detail_resp.json()["data"]
    assert updated["name"] == "SQA Primary Site Updated"
    assert updated["address"] == "300 SQA Site Road"
    assert updated["description"] == "SQA site edit path"

    page.once("dialog", lambda dialog: dialog.accept())
    await updated_row.get_by_title("Delete").click()
    await expect(page.locator("td", has_text=code)).to_be_hidden(timeout=8_000)

    delete_resp = api.get(f"{API_SITES}/{created['id']}")
    assert delete_resp.status_code == 404, delete_resp.text


@pytest.mark.ui
@pytest.mark.usefixtures("physical_model_cleanup")
async def test_area_crud(page: Page, api) -> None:
    site = _create_site(api, name="SQA Area Parent Site")
    code = _unique_code("SQA_AR")

    await _open_areas_page(page, site_id=site["id"], site_name=site["name"])
    await page.get_by_role("button", name="New Area").click()
    await expect(page.get_by_role("heading", name="New Area")).to_be_visible(timeout=5_000)

    await page.locator("input[name='code']").fill(code)
    await page.locator("input[name='name']").fill("SQA Mixing Area")
    await page.locator("textarea[name='description']").fill("SQA area create path")
    await page.locator("button[type='submit']").click()

    row = page.locator("tr").filter(has_text=code)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text="SQA Mixing Area")).to_be_visible()

    list_resp = api.get(f"{API_SITES}/{site['id']}/areas", params={"limit": "200"})
    assert list_resp.status_code == 200, list_resp.text
    created = next((item for item in list_resp.json()["data"] if item["code"] == code), None)
    assert created is not None
    assert created["name"] == "SQA Mixing Area"
    assert created["description"] == "SQA area create path"

    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Area")).to_be_visible(timeout=5_000)

    await page.locator("input[name='name']").fill("SQA Packing Area")
    await page.locator("textarea[name='description']").fill("SQA area edit path")
    await page.locator("button[type='submit']").click()

    updated_row = page.locator("tr").filter(has_text=code)
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.locator("td", has_text="SQA Packing Area")).to_be_visible()

    detail_resp = api.get(f"/areas/{created['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    updated = detail_resp.json()["data"]
    assert updated["name"] == "SQA Packing Area"
    assert updated["description"] == "SQA area edit path"

    page.once("dialog", lambda dialog: dialog.accept())
    await updated_row.get_by_title("Delete").click()
    await expect(page.locator("td", has_text=code)).to_be_hidden(timeout=8_000)

    delete_resp = api.get(f"/areas/{created['id']}")
    assert delete_resp.status_code == 404, delete_resp.text


@pytest.mark.ui
@pytest.mark.usefixtures("physical_model_cleanup")
async def test_line_crud(page: Page, api) -> None:
    site = _create_site(api, name="SQA Line Parent Site")
    area = _create_area(api, site_id=site["id"], name="SQA Line Parent Area")
    code = _unique_code("SQA_LN")

    await _open_lines_page(page, area_id=area["id"], area_name=area["name"])
    await page.get_by_role("button", name="New Line").click()
    await expect(page.get_by_role("heading", name="New Line")).to_be_visible(timeout=5_000)

    await page.locator("input[name='code']").fill(code)
    await page.locator("input[name='name']").fill("SQA Filling Line")
    await page.locator("textarea[name='description']").fill("SQA line create path")
    await page.locator("button[type='submit']").click()

    row = page.locator("tr").filter(has_text=code)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text="SQA Filling Line")).to_be_visible()

    list_resp = api.get(f"/areas/{area['id']}/lines", params={"limit": "200"})
    assert list_resp.status_code == 200, list_resp.text
    created = next((item for item in list_resp.json()["data"] if item["code"] == code), None)
    assert created is not None
    assert created["name"] == "SQA Filling Line"
    assert created["description"] == "SQA line create path"

    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Line")).to_be_visible(timeout=5_000)

    await page.locator("input[name='name']").fill("SQA Labeling Line")
    await page.locator("textarea[name='description']").fill("SQA line edit path")
    await page.locator("button[type='submit']").click()

    updated_row = page.locator("tr").filter(has_text=code)
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.locator("td", has_text="SQA Labeling Line")).to_be_visible()

    detail_resp = api.get(f"/lines/{created['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    updated = detail_resp.json()["data"]
    assert updated["name"] == "SQA Labeling Line"
    assert updated["description"] == "SQA line edit path"

    page.once("dialog", lambda dialog: dialog.accept())
    await updated_row.get_by_title("Delete").click()
    await expect(page.locator("td", has_text=code)).to_be_hidden(timeout=8_000)

    delete_resp = api.get(f"/lines/{created['id']}")
    assert delete_resp.status_code == 404, delete_resp.text


@pytest.mark.ui
@pytest.mark.usefixtures("physical_model_cleanup")
async def test_work_cell_crud(page: Page, api) -> None:
    site = _create_site(api, name="SQA WC Parent Site")
    area = _create_area(api, site_id=site["id"], name="SQA WC Parent Area")
    line = _create_line(api, area_id=area["id"], name="SQA WC Parent Line")
    code = _unique_code("SQA_WC")

    await _open_work_cells_page(page, line_id=line["id"], line_name=line["name"])
    await page.get_by_role("button", name="New Work Cell").click()
    await expect(page.get_by_role("heading", name="New Work Cell")).to_be_visible(timeout=5_000)

    await page.locator("input[name='code']").fill(code)
    await page.locator("input[name='name']").fill("SQA Manual Cell")
    await page.locator("textarea[name='description']").fill("SQA work cell create path")
    await page.locator("select[name='default_dispatch_strategy']").select_option("manual")
    await page.locator("button[type='submit']").click()

    row = page.locator("tr").filter(has_text=code)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text="SQA Manual Cell")).to_be_visible()

    list_resp = api.get(f"/lines/{line['id']}/work-cells", params={"limit": "200"})
    assert list_resp.status_code == 200, list_resp.text
    created = next((item for item in list_resp.json()["data"] if item["code"] == code), None)
    assert created is not None
    assert created["name"] == "SQA Manual Cell"
    assert created["description"] == "SQA work cell create path"
    assert created["default_dispatch_strategy"] == "manual"

    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Work Cell")).to_be_visible(timeout=5_000)

    await page.locator("input[name='name']").fill("SQA Queue Cell")
    await page.locator("textarea[name='description']").fill("SQA work cell edit path")
    await page.locator("select[name='default_dispatch_strategy']").select_option("shortest_queue")
    await page.locator("button[type='submit']").click()

    updated_row = page.locator("tr").filter(has_text=code)
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.locator("td", has_text="SQA Queue Cell")).to_be_visible()

    detail_resp = api.get(f"/work-cells/{created['id']}")
    assert detail_resp.status_code == 200, detail_resp.text
    updated = detail_resp.json()["data"]
    assert updated["name"] == "SQA Queue Cell"
    assert updated["description"] == "SQA work cell edit path"
    assert updated["default_dispatch_strategy"] == "shortest_queue"

    page.once("dialog", lambda dialog: dialog.accept())
    await updated_row.get_by_title("Delete").click()
    await expect(page.locator("td", has_text=code)).to_be_hidden(timeout=8_000)

    delete_resp = api.get(f"/work-cells/{created['id']}")
    assert delete_resp.status_code == 404, delete_resp.text