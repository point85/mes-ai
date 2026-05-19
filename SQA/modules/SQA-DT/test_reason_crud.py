"""
SQA-DT -- Reason code editor CRUD tests.

Surfaces:
- DT-CLIENT /reasons page
- MES REST API /api/v1/performance/reasons

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
DT_REASONS_URL = f"{_DT_BASE}/reasons"
API_REASONS = "/performance/reasons"


def _unique_code() -> str:
    return uuid4().hex[:4].upper()


def _list_reasons(api) -> list[dict]:
    resp = api.get(API_REASONS)
    assert resp.status_code == 200, f"List reasons failed: {resp.text}"
    return resp.json().get("data", [])


def _find_reason_by_code(api, code: str) -> dict | None:
    return next((item for item in _list_reasons(api) if item.get("code") == code), None)


def _create_reason(api, **overrides) -> dict:
    payload = {
        "code": _unique_code(),
        "name": "SQA Seeded Reason",
        "description": "SQA seeded reason",
        "oee_bucket": "downtime_unplanned",
        "parent_id": None,
    }
    payload.update(overrides)
    resp = api.post(API_REASONS, json=payload)
    assert resp.status_code in (200, 201), f"Reason setup failed: {resp.text}"
    return resp.json()["data"]


async def _open_reasons_page(page: Page) -> None:
    await page.goto(DT_REASONS_URL)
    await expect(page.get_by_role("heading", name="Reason Codes")).to_be_visible(timeout=10_000)


async def _open_new_reason_dialog(page: Page) -> None:
    await page.get_by_role("button", name="New Reason").click()
    await expect(page.get_by_role("heading", name="New Reason")).to_be_visible(timeout=5_000)


async def _fill_reason_form(
    page: Page,
    *,
    code: str | None = None,
    name: str,
    description: str,
    oee_bucket: str,
    parent_id: str | None = None,
) -> None:
    if code is not None:
        await page.locator("input[name='code']").fill(code)
    await page.locator("input[name='name']").fill(name)
    await page.locator("textarea[name='description']").fill(description)
    await page.locator("select[name='oee_bucket']").select_option(value=oee_bucket)
    if parent_id is not None:
        await page.locator("select[name='parent_id']").select_option(value=parent_id)


async def _submit_dialog(page: Page) -> None:
    await page.locator("button[type='submit']").click()


@pytest.mark.ui
@pytest.mark.usefixtures("reason_cleanup")
async def test_reason_create(page: Page, api) -> None:
    code = _unique_code()

    await _open_reasons_page(page)
    await _open_new_reason_dialog(page)
    await _fill_reason_form(
        page,
        code=code,
        name="SQA Root Reason",
        description="SQA create reason",
        oee_bucket="downtime_planned",
    )
    await _submit_dialog(page)

    row = page.locator("tr").filter(has_text=code)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text="SQA Root Reason")).to_be_visible()
    await expect(row.locator("td", has_text="Planned DT")).to_be_visible()

    created = _find_reason_by_code(api, code)
    assert created is not None
    assert created["name"] == "SQA Root Reason"
    assert created["description"] == "SQA create reason"
    assert created["oee_bucket"] == "downtime_planned"
    assert created["parent_id"] is None


@pytest.mark.ui
@pytest.mark.usefixtures("reason_cleanup")
async def test_reason_edit(page: Page, api) -> None:
    reason = _create_reason(
        api,
        name="SQA Editable Reason",
        description="SQA editable reason",
        oee_bucket="downtime_unplanned",
    )

    await _open_reasons_page(page)

    row = page.locator("tr").filter(has_text=reason["code"])
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Reason")).to_be_visible(timeout=5_000)

    await _fill_reason_form(
        page,
        name="SQA Edited Reason",
        description="SQA edited reason",
        oee_bucket="uptime_non_value",
    )
    await _submit_dialog(page)

    updated_row = page.locator("tr").filter(has_text=reason["code"])
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row).to_contain_text("SQA Edited Reason")
    await expect(updated_row).to_contain_text("Non-Value")

    resp = api.get(f"{API_REASONS}/{reason['id']}")
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]
    assert updated["name"] == "SQA Edited Reason"
    assert updated["description"] == "SQA edited reason"
    assert updated["oee_bucket"] == "uptime_non_value"


@pytest.mark.ui
@pytest.mark.usefixtures("reason_cleanup")
async def test_reason_delete(page: Page, api) -> None:
    reason = _create_reason(
        api,
        name="SQA Delete Reason",
        description="SQA delete reason",
    )

    await _open_reasons_page(page)

    row = page.locator("tr").filter(has_text=reason["code"])
    await expect(row).to_be_visible(timeout=8_000)

    page.once("dialog", lambda dialog: dialog.accept())
    await row.get_by_title("Delete").click()

    await expect(page.locator("td", has_text=reason["code"])).to_be_hidden(timeout=8_000)

    resp = api.get(f"{API_REASONS}/{reason['id']}")
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}: {resp.text}"


@pytest.mark.ui
@pytest.mark.usefixtures("reason_cleanup")
async def test_reason_add_child(page: Page, api) -> None:
    parent = _create_reason(
        api,
        code=_unique_code(),
        name="SQA Parent Reason",
        description="SQA parent reason",
        oee_bucket="downtime_unplanned",
    )
    child_code = _unique_code()

    await _open_reasons_page(page)

    row = page.locator("tr").filter(has_text=parent["code"])
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Add child reason").click()
    await expect(page.get_by_role("heading", name="New Reason")).to_be_visible(timeout=5_000)
    await expect(page.locator("select[name='parent_id']")).to_have_value(parent["id"])

    await _fill_reason_form(
        page,
        code=child_code,
        name="SQA Child Reason",
        description="SQA child reason",
        oee_bucket="excluded",
        parent_id=parent["id"],
    )
    await _submit_dialog(page)

    child_row = page.locator("tr").filter(has_text=child_code)
    await expect(child_row).to_be_visible(timeout=8_000)
    await expect(child_row).to_contain_text("SQA Child Reason")
    await expect(child_row).to_contain_text("Excluded")

    created = _find_reason_by_code(api, child_code)
    assert created is not None
    assert created["name"] == "SQA Child Reason"
    assert created["description"] == "SQA child reason"
    assert created["oee_bucket"] == "excluded"
    assert created["parent_id"] == parent["id"]