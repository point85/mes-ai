"""
SQA-DT -- Data Definitions CRUD and filter tests.

Surfaces:
- DT-CLIENT /data-definitions page
- MES REST API /api/v1/data/definitions

Pattern:
- setup and cleanup via API
- UI action via Playwright
- API oracle after each UI mutation
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from playwright.async_api import Page, expect

DT_DATA_DEFINITION_URL = "http://localhost:5177/data-definitions"
API_DATA_DEFINITIONS = "/data/definitions"


def _unique_code(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


async def _open_data_definitions_page(page: Page) -> None:
    await page.goto(DT_DATA_DEFINITION_URL)
    await expect(
        page.get_by_role("heading", name="Data Definitions")
    ).to_be_visible(timeout=10_000)


async def _open_new_definition_dialog(page: Page) -> None:
    await page.get_by_role("button", name="New Definition").click()
    await expect(
        page.get_by_role("heading", name="New Data Definition")
    ).to_be_visible(timeout=5_000)


async def _fill_definition_form(
    page: Page,
    *,
    code: str,
    name: str,
    source: str = "manual",
    data_type: str = "numeric",
    is_required: bool = False,
    lower_limit: str | None = None,
    upper_limit: str | None = None,
    enum_values: str | None = None,
    description: str | None = None,
) -> None:
    await page.locator("input[name='code']").fill(code)
    await page.locator("select[name='source']").select_option(value=source)
    await page.locator("input[name='name']").fill(name)
    await page.locator("select[name='data_type']").select_option(value=data_type)

    required_checkbox = page.locator("input[name='is_required']")
    if await required_checkbox.is_checked() != is_required:
        await required_checkbox.click()

    if data_type == "numeric":
        if lower_limit is not None:
            await page.locator("input[name='lower_limit']").fill(lower_limit)
        if upper_limit is not None:
            await page.locator("input[name='upper_limit']").fill(upper_limit)

    if data_type == "enum" and enum_values is not None:
        await page.locator("input[name='enum_values']").fill(enum_values)

    if description is not None:
        await page.locator("textarea[name='description']").fill(description)


async def _submit_dialog(page: Page) -> None:
    await page.locator("button[type='submit']").click()


def _create_definition(api, **overrides):
    payload = {
        "code": "SQA_DD_BASE",
        "name": "SQA Data Definition",
        "data_type": "numeric",
        "source": "manual",
        "is_required": False,
        "lower_limit": 1.5,
        "upper_limit": 9.5,
        "description": "SQA seeded definition",
    }
    payload.update(overrides)
    resp = api.post(API_DATA_DEFINITIONS, json=payload)
    assert resp.status_code in (200, 201), f"API setup failed: {resp.text}"
    return resp.json()["data"]


def _find_definition_by_code(api, code: str):
    resp = api.get(API_DATA_DEFINITIONS, params={"limit": "200"})
    assert resp.status_code == 200, f"List definitions failed: {resp.text}"
    for item in resp.json().get("data", []):
        if item.get("code") == code:
            return item
    return None


@pytest.mark.ui
@pytest.mark.usefixtures("data_definition_cleanup")
async def test_data_definition_create(page: Page, api) -> None:
    code = _unique_code("SQA_DD_TEMP")
    name = "SQA Temperature"

    await _open_data_definitions_page(page)
    await _open_new_definition_dialog(page)
    await _fill_definition_form(
        page,
        code=code,
        name=name,
        source="manual",
        data_type="numeric",
        is_required=True,
        lower_limit="10",
        upper_limit="20",
        description="SQA numeric definition",
    )
    await _submit_dialog(page)

    row = page.locator("tr").filter(has_text=code)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text=name)).to_be_visible()

    created = _find_definition_by_code(api, code)
    assert created is not None
    assert created["name"] == name
    assert created["data_type"] == "numeric"
    assert created["source"] == "manual"
    assert created["is_required"] is True
    assert created["lower_limit"] == 10
    assert created["upper_limit"] == 20


@pytest.mark.ui
@pytest.mark.usefixtures("data_definition_cleanup")
async def test_data_definition_edit(page: Page, api) -> None:
    definition = _create_definition(
        api,
        code=_unique_code("SQA_DD_EDIT"),
        name="SQA Editable Definition",
        source="manual",
        data_type="numeric",
        is_required=False,
        lower_limit=2,
        upper_limit=8,
    )

    await _open_data_definitions_page(page)

    row = page.locator("tr").filter(has_text=definition["code"])
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Edit").click()
    await expect(
        page.get_by_role("heading", name="Edit Data Definition")
    ).to_be_visible(timeout=5_000)

    await _fill_definition_form(
        page,
        code=definition["code"],
        name="SQA Edited Definition",
        source="sensor",
        data_type="enum",
        is_required=True,
        enum_values="pass,fail,rework",
        description="Edited by SQA",
    )
    await _submit_dialog(page)

    await expect(page.locator("tr").filter(has_text="SQA Edited Definition")).to_be_visible(timeout=8_000)

    resp = api.get(f"{API_DATA_DEFINITIONS}/{definition['id']}")
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]
    assert updated["name"] == "SQA Edited Definition"
    assert updated["source"] == "sensor"
    assert updated["data_type"] == "enum"
    assert updated["enum_values"] == "pass,fail,rework"
    assert updated["is_required"] is True


@pytest.mark.ui
@pytest.mark.usefixtures("data_definition_cleanup")
async def test_data_definition_delete(page: Page, api) -> None:
    definition = _create_definition(
        api,
        code=_unique_code("SQA_DD_DELETE"),
        name="SQA Delete Definition",
    )

    await _open_data_definitions_page(page)

    row = page.locator("tr").filter(has_text=definition["code"])
    await expect(row).to_be_visible(timeout=8_000)

    page.on("dialog", lambda dialog: dialog.accept())
    await row.get_by_title("Delete").click()

    await expect(page.locator("td", has_text=definition["code"])).to_be_hidden(timeout=8_000)

    resp = api.get(f"{API_DATA_DEFINITIONS}/{definition['id']}")
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}: {resp.text}"


@pytest.mark.ui
@pytest.mark.usefixtures("data_definition_cleanup")
async def test_data_definition_filters(page: Page, api) -> None:
    numeric_code = _unique_code("SQA_DD_NUMERIC")
    enum_code = _unique_code("SQA_DD_ENUM")

    _create_definition(
        api,
        code=numeric_code,
        name="SQA Numeric Definition",
        data_type="numeric",
        source="manual",
    )
    _create_definition(
        api,
        code=enum_code,
        name="SQA Enum Definition",
        data_type="enum",
        source="sensor",
        enum_values="pass,fail",
    )

    await _open_data_definitions_page(page)

    type_filter = page.locator("label:has-text('Type:') + select")
    source_filter = page.locator("label:has-text('Source:') + select")

    await type_filter.select_option(value="enum")
    await expect(page.locator("td", has_text=enum_code).first).to_be_visible(timeout=5_000)
    await expect(page.locator("td", has_text=numeric_code)).to_be_hidden()

    await source_filter.select_option(value="sensor")
    await expect(page.locator("td", has_text=enum_code).first).to_be_visible(timeout=5_000)

    await source_filter.select_option(value="manual")
    await expect(page.locator("td", has_text=enum_code)).to_be_hidden()

    await type_filter.select_option(value="")
    await source_filter.select_option(value="")
    await expect(page.locator("td", has_text=numeric_code).first).to_be_visible(timeout=5_000)
    await expect(page.locator("td", has_text=enum_code).first).to_be_visible(timeout=5_000)