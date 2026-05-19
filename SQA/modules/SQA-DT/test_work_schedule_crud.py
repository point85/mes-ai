"""
SQA-DT — Work Schedule CRUD editor tests.

Surfaces: DT-CLIENT /work-schedules page + MES REST API /api/v1/work-schedules

Authoring rules (enforced):
- Every UI action is followed by an API oracle confirming persistence.
- Test data is isolated with an SQA-prefixed work schedule name.
- Setup and teardown use the REST API to keep tests deterministic.
"""
from __future__ import annotations

import pytest
from playwright.async_api import Page, expect

import os
_DT_BASE = os.environ.get("SQA_DT_URL", "http://localhost:5177")
DT_WORK_SCHEDULE_URL = f"{_DT_BASE}/work-schedules"
API_WORK_SCHEDULE = "/work-schedules"


def _list_schedules(api):
    return api.get(API_WORK_SCHEDULE)


def _find_schedule_by_name(api, name: str):
    resp = _list_schedules(api)
    assert resp.status_code == 200, f"List schedules failed: {resp.text}"
    items = resp.json().get("data", [])
    return next((item for item in items if item.get("name") == name), None)


def _get_schedule(api, schedule_id: str):
    return api.get(f"{API_WORK_SCHEDULE}/{schedule_id}")


def _create_schedule(api, name: str, description: str | None):
    resp = api.post(API_WORK_SCHEDULE, json={"name": name, "description": description})
    assert resp.status_code in (200, 201), f"Create schedule failed ({name}): {resp.text}"
    return resp.json()["data"]


def _delete_schedule_if_present(api, name: str) -> None:
    found = _find_schedule_by_name(api, name)
    if found is not None:
        api.delete(f"{API_WORK_SCHEDULE}/{found['id']}")


@pytest.fixture
def work_schedule_cleanup(api):
    names = [
        "SQA Work Schedule Alpha",
        "SQA Work Schedule Beta",
        "SQA Work Schedule Gamma",
    ]
    for name in names:
        _delete_schedule_if_present(api, name)
    yield
    for name in names:
        _delete_schedule_if_present(api, name)


async def _open_work_schedule_page(page: Page) -> None:
    await page.goto(DT_WORK_SCHEDULE_URL)
    await expect(page.get_by_role("heading", name="Work Schedules")).to_be_visible(timeout=10_000)


async def _open_new_schedule_dialog(page: Page) -> None:
    await page.get_by_role("button", name="New Schedule").click()
    await expect(page.get_by_role("heading", name="New Work Schedule")).to_be_visible(timeout=5_000)


async def _fill_schedule_form(page: Page, *, name: str, description: str) -> None:
    dialog = page.locator("form")
    await dialog.get_by_role("textbox").nth(0).fill(name)
    await dialog.get_by_role("textbox").nth(1).fill(description)


async def _submit_dialog(page: Page) -> None:
    await page.locator("button[type='submit']").click()


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_cleanup")
async def test_work_schedule_create(page: Page, api) -> None:
    """TC-WS-001 — Create a work schedule via the UI and verify via API."""
    name = "SQA Work Schedule Alpha"
    description = "SQA alpha schedule"

    await _open_work_schedule_page(page)
    await _open_new_schedule_dialog(page)
    await _fill_schedule_form(page, name=name, description=description)
    await _submit_dialog(page)

    row = page.locator("tr").filter(has_text=name)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text=description)).to_be_visible(timeout=8_000)

    created = _find_schedule_by_name(api, name)
    assert created is not None, "Created work schedule not found via API"

    resp = _get_schedule(api, created["id"])
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()["data"]
    assert data["name"] == name
    assert data["description"] == description
    assert data["shifts"] == []
    assert data["rotations"] == []
    assert data["teams"] == []
    assert data["non_working_periods"] == []


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_cleanup")
async def test_work_schedule_edit(page: Page, api) -> None:
    """TC-WS-002 — Edit an existing work schedule via the UI and verify via API."""
    original_name = "SQA Work Schedule Alpha"
    updated_name = "SQA Work Schedule Beta"
    original_description = "SQA alpha schedule"
    updated_description = "SQA beta schedule"

    _create_schedule(api, original_name, original_description)

    await _open_work_schedule_page(page)

    row = page.locator("tr").filter(has_text=original_name)
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Work Schedule")).to_be_visible(timeout=5_000)

    await _fill_schedule_form(page, name=updated_name, description=updated_description)
    await _submit_dialog(page)

    updated_row = page.locator("tr").filter(has_text=updated_name)
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(page.locator("tr").filter(has_text=original_name)).to_be_hidden(timeout=8_000)

    updated = _find_schedule_by_name(api, updated_name)
    assert updated is not None, "Updated work schedule not found via API"

    resp = _get_schedule(api, updated["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == updated_name
    assert data["description"] == updated_description


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_cleanup")
async def test_work_schedule_delete(page: Page, api) -> None:
    """TC-WS-003 — Delete a work schedule via the UI and verify it is removed via API."""
    name = "SQA Work Schedule Gamma"
    description = "SQA gamma schedule"

    created = _create_schedule(api, name, description)

    await _open_work_schedule_page(page)

    row = page.locator("tr").filter(has_text=name)
    await expect(row).to_be_visible(timeout=8_000)

    async def _accept_dialog(dialog) -> None:
        await dialog.accept()

    page.once("dialog", _accept_dialog)
    await row.get_by_title("Delete").click()

    await expect(page.locator("tr").filter(has_text=name)).to_be_hidden(timeout=8_000)

    resp = _get_schedule(api, created["id"])
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}: {resp.text}"


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_cleanup")
async def test_work_schedule_open_detail(page: Page, api) -> None:
    """TC-WS-004 — Open the work schedule detail page and verify tabs render."""
    name = "SQA Work Schedule Alpha"
    description = "SQA alpha schedule"

    created = _create_schedule(api, name, description)

    await _open_work_schedule_page(page)

    row = page.locator("tr").filter(has_text=name)
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Open detail").click()

    await expect(page).to_have_url(f"{DT_WORK_SCHEDULE_URL}/{created['id']}")
    await expect(page.get_by_role("heading", name=name)).to_be_visible(timeout=8_000)
    await expect(page.get_by_role("button", name="Shifts")).to_be_visible()
    await expect(page.get_by_role("button", name="Rotations")).to_be_visible()
    await expect(page.get_by_role("button", name="Teams")).to_be_visible()
    await expect(page.get_by_role("button", name="Non-Working Periods")).to_be_visible()

    resp = _get_schedule(api, created["id"])
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == name