"""
SQA-DT — Work Schedule shift CRUD editor tests.

Surfaces: DT-CLIENT /work-schedules/:id detail page (Shifts tab)
          + MES REST API /api/v1/work-schedules

Authoring rules (enforced):
- Every UI action is followed by an API oracle confirming persistence.
- Test data is isolated with SQA-prefixed schedule, shift, and break names.
- Setup and teardown use the REST API to keep tests deterministic.
"""
from __future__ import annotations

import pytest
from playwright.async_api import Page, expect

DT_WORK_SCHEDULE_URL = "http://localhost:5177/work-schedules"
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


def _create_shift(api, schedule_id: str, name: str, description: str | None, start_time: str, duration_seconds: int):
    resp = api.post(
        f"{API_WORK_SCHEDULE}/{schedule_id}/shifts",
        json={
            "name": name,
            "description": description,
            "start_time": start_time,
            "duration_seconds": duration_seconds,
        },
    )
    assert resp.status_code in (200, 201), f"Create shift failed ({name}): {resp.text}"
    return resp.json()["data"]


def _delete_schedule_if_present(api, name: str) -> None:
    found = _find_schedule_by_name(api, name)
    if found is not None:
        api.delete(f"{API_WORK_SCHEDULE}/{found['id']}")


@pytest.fixture
def work_schedule_shift_cleanup(api):
    _delete_schedule_if_present(api, "SQA Shift Schedule")
    yield
    _delete_schedule_if_present(api, "SQA Shift Schedule")


async def _open_schedule_detail(page: Page, schedule_id: str) -> None:
    await page.goto(f"{DT_WORK_SCHEDULE_URL}/{schedule_id}")
    await expect(page.get_by_role("button", name="Shifts")).to_be_visible(timeout=10_000)
    await expect(page.get_by_role("button", name="New Shift")).to_be_visible(timeout=10_000)


async def _open_new_shift_dialog(page: Page) -> None:
    await page.get_by_role("button", name="New Shift").click()
    await expect(page.get_by_role("heading", name="New Shift")).to_be_visible(timeout=5_000)


async def _fill_shift_form(page: Page, *, name: str, description: str, start_time: str, hours: str, minutes: str) -> None:
    await page.locator("label:has-text('Name *') + input").fill(name)
    await page.locator("label:has-text('Description') + input").fill(description)
    await page.locator("label:has-text('Start Time') + input").fill(start_time)
    await page.locator("label:has-text('Hours') + input").fill(hours)
    await page.locator("label:has-text('Minutes') + input").fill(minutes)


async def _submit_dialog(page: Page) -> None:
    await page.locator("button[type='submit']").click()


def _shift_card(page: Page, shift_name: str):
    return page.locator("div.rounded-lg.border.border-gray-200.bg-white.shadow-sm").filter(has_text=shift_name)


def _break_row(shift_card, break_name: str):
    return shift_card.locator("div.flex.items-center.gap-3.text-sm").filter(has_text=break_name)


def _find_shift(schedule_data: dict, name: str):
    return next((shift for shift in schedule_data.get("shifts", []) if shift.get("name") == name), None)


def _find_break(shift_data: dict, name: str):
    return next((brk for brk in shift_data.get("breaks", []) if brk.get("name") == name), None)


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_shift_cleanup")
async def test_work_schedule_shift_create(page: Page, api) -> None:
    """TC-WS-SHIFT-001 — Create a shift in the Shifts tab and verify via API."""
    schedule = _create_schedule(api, "SQA Shift Schedule", "SQA shift schedule")
    shift_name = "SQA Day Shift"
    shift_description = "SQA primary shift"

    await _open_schedule_detail(page, schedule["id"])
    await _open_new_shift_dialog(page)
    await _fill_shift_form(
        page,
        name=shift_name,
        description=shift_description,
        start_time="06:00",
        hours="8",
        minutes="30",
    )
    await _submit_dialog(page)

    shift_card = _shift_card(page, shift_name)
    await expect(shift_card).to_be_visible(timeout=8_000)
    await expect(shift_card.get_by_text("06:00", exact=True)).to_be_visible(timeout=8_000)
    await expect(shift_card.get_by_text("8h 30m", exact=True)).to_be_visible(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()["data"]
    shift = _find_shift(data, shift_name)
    assert shift is not None, "Created shift not found via API"
    assert shift["description"] == shift_description
    assert shift["start_time"] == "06:00:00"
    assert shift["duration_seconds"] == 30600


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_shift_cleanup")
async def test_work_schedule_shift_edit(page: Page, api) -> None:
    """TC-WS-SHIFT-002 — Edit an existing shift and verify via API."""
    schedule = _create_schedule(api, "SQA Shift Schedule", "SQA shift schedule")
    _create_shift(api, schedule["id"], "SQA Day Shift", "SQA primary shift", "06:00:00", 28800)

    await _open_schedule_detail(page, schedule["id"])

    shift_card = _shift_card(page, "SQA Day Shift")
    await expect(shift_card).to_be_visible(timeout=8_000)
    await shift_card.locator("button").nth(1).click()
    await expect(page.get_by_role("heading", name="Edit Shift")).to_be_visible(timeout=5_000)

    await _fill_shift_form(
        page,
        name="SQA Evening Shift",
        description="SQA updated shift",
        start_time="14:15",
        hours="9",
        minutes="0",
    )
    await _submit_dialog(page)

    updated_card = _shift_card(page, "SQA Evening Shift")
    await expect(updated_card).to_be_visible(timeout=8_000)
    await expect(updated_card.get_by_text("14:15", exact=True)).to_be_visible(timeout=8_000)
    await expect(updated_card.get_by_text("9h 0m", exact=True)).to_be_visible(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    shift = _find_shift(data, "SQA Evening Shift")
    assert shift is not None, "Updated shift not found via API"
    assert shift["description"] == "SQA updated shift"
    assert shift["start_time"] == "14:15:00"
    assert shift["duration_seconds"] == 32400


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_shift_cleanup")
async def test_work_schedule_shift_delete(page: Page, api) -> None:
    """TC-WS-SHIFT-003 — Delete a shift and verify it is removed via API."""
    schedule = _create_schedule(api, "SQA Shift Schedule", "SQA shift schedule")
    _create_shift(api, schedule["id"], "SQA Day Shift", "SQA primary shift", "06:00:00", 28800)

    await _open_schedule_detail(page, schedule["id"])

    shift_card = _shift_card(page, "SQA Day Shift")
    await expect(shift_card).to_be_visible(timeout=8_000)

    async def _accept_dialog(dialog) -> None:
        await dialog.accept()

    page.once("dialog", _accept_dialog)
    await shift_card.locator("button").nth(2).click()

    await expect(_shift_card(page, "SQA Day Shift")).to_be_hidden(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert _find_shift(data, "SQA Day Shift") is None, "Deleted shift still present via API"


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_shift_cleanup")
async def test_work_schedule_add_break(page: Page, api) -> None:
    """TC-WS-SHIFT-004 — Add and remove a break from an expanded shift and verify via API."""
    schedule = _create_schedule(api, "SQA Shift Schedule", "SQA shift schedule")
    _create_shift(api, schedule["id"], "SQA Day Shift", "SQA primary shift", "06:00:00", 28800)

    await _open_schedule_detail(page, schedule["id"])

    shift_card = _shift_card(page, "SQA Day Shift")
    await expect(shift_card).to_be_visible(timeout=8_000)
    await shift_card.locator("button").nth(0).click()

    await expect(shift_card.get_by_role("button", name="Add Break")).to_be_visible(timeout=5_000)
    await shift_card.get_by_role("button", name="Add Break").click()
    await expect(page.get_by_role("heading", name="Add Break")).to_be_visible(timeout=5_000)

    await page.locator("label:has-text('Name *') + input").fill("SQA Lunch Break")
    await page.locator("label:has-text('Start Time') + input").fill("10:30")
    await page.locator("label:has-text('Duration (minutes)') + input").fill("30")
    await _submit_dialog(page)

    break_row = _break_row(shift_card, "SQA Lunch Break")
    await expect(break_row).to_be_visible(timeout=8_000)
    await expect(break_row.get_by_text("10:30", exact=True)).to_be_visible(timeout=8_000)
    await expect(break_row.get_by_text("30m", exact=True)).to_be_visible(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    shift = _find_shift(data, "SQA Day Shift")
    assert shift is not None
    brk = _find_break(shift, "SQA Lunch Break")
    assert brk is not None, "Created break not found via API"
    assert brk["start_time"] == "10:30:00"
    assert brk["duration_seconds"] == 1800

    await break_row.locator("button").click()
    await expect(_break_row(shift_card, "SQA Lunch Break")).to_be_hidden(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    shift = _find_shift(data, "SQA Day Shift")
    assert shift is not None
    assert _find_break(shift, "SQA Lunch Break") is None, "Deleted break still present via API"