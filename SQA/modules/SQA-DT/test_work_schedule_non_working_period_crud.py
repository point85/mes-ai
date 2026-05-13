"""
SQA-DT — Work Schedule non-working period CRUD editor tests.

Surfaces: DT-CLIENT /work-schedules/:id detail page (Non-Working Periods tab)
          + MES REST API /api/v1/work-schedules
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


def _create_period(api, schedule_id: str, name: str, description: str | None, start_datetime: str, duration_seconds: int):
    resp = api.post(
        f"{API_WORK_SCHEDULE}/{schedule_id}/non-working-periods",
        json={
            "name": name,
            "description": description,
            "start_datetime": start_datetime,
            "duration_seconds": duration_seconds,
        },
    )
    assert resp.status_code in (200, 201), f"Create non-working period failed ({name}): {resp.text}"
    return resp.json()["data"]


def _delete_schedule_if_present(api, name: str) -> None:
    found = _find_schedule_by_name(api, name)
    if found is not None:
        api.delete(f"{API_WORK_SCHEDULE}/{found['id']}")


@pytest.fixture
def work_schedule_nwp_cleanup(api):
    _delete_schedule_if_present(api, "SQA NWP Schedule")
    yield
    _delete_schedule_if_present(api, "SQA NWP Schedule")


async def _open_schedule_detail(page: Page, schedule_id: str) -> None:
    await page.goto(f"{DT_WORK_SCHEDULE_URL}/{schedule_id}")
    await expect(page.get_by_role("button", name="Non-Working Periods")).to_be_visible(timeout=10_000)


async def _open_non_working_tab(page: Page) -> None:
    await page.get_by_role("button", name="Non-Working Periods").click()
    await expect(page.get_by_role("button", name="Add Period")).to_be_visible(timeout=8_000)


async def _fill_nwp_form(page: Page, *, name: str, description: str, start_dt: str, days: str, hours: str) -> None:
    await page.locator("label:has-text('Name *') + input").fill(name)
    await page.locator("label:has-text('Description') + input").fill(description)
    await page.locator("label:has-text('Start Date/Time *') + input").fill(start_dt)
    await page.locator("label:has-text('Days') + input").fill(days)
    await page.locator("label:has-text('Hours') + input").fill(hours)


async def _submit_dialog(page: Page) -> None:
    await page.locator("button[type='submit']").click()


def _find_period(schedule_data: dict, name: str):
    return next((period for period in schedule_data.get("non_working_periods", []) if period.get("name") == name), None)


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_nwp_cleanup")
async def test_work_schedule_non_working_period_create(page: Page, api) -> None:
    schedule = _create_schedule(api, "SQA NWP Schedule", "SQA non-working schedule")

    await _open_schedule_detail(page, schedule["id"])
    await _open_non_working_tab(page)

    await page.get_by_role("button", name="Add Period").click()
    await expect(page.get_by_role("heading", name="New Non-Working Period")).to_be_visible(timeout=5_000)
    await _fill_nwp_form(
        page,
        name="SQA Plant Shutdown",
        description="SQA planned outage",
        start_dt="2026-05-20T00:00",
        days="1",
        hours="8",
    )
    await _submit_dialog(page)

    row = page.locator("tr").filter(has_text="SQA Plant Shutdown")
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.get_by_text("2026-05-20 00:00", exact=True)).to_be_visible(timeout=8_000)
    await expect(row.get_by_text("1d 8h", exact=True)).to_be_visible(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    period = _find_period(data, "SQA Plant Shutdown")
    assert period is not None
    assert period["description"] == "SQA planned outage"
    assert period["start_datetime"].startswith("2026-05-20T00:00:00")
    assert period["duration_seconds"] == 115200


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_nwp_cleanup")
async def test_work_schedule_non_working_period_edit(page: Page, api) -> None:
    schedule = _create_schedule(api, "SQA NWP Schedule", "SQA non-working schedule")
    _create_period(api, schedule["id"], "SQA Plant Shutdown", "SQA planned outage", "2026-05-20T00:00:00", 86400)

    await _open_schedule_detail(page, schedule["id"])
    await _open_non_working_tab(page)

    row = page.locator("tr").filter(has_text="SQA Plant Shutdown")
    await expect(row).to_be_visible(timeout=8_000)
    await row.locator("button").nth(0).click()
    await expect(page.get_by_role("heading", name="Edit Period")).to_be_visible(timeout=5_000)
    await _fill_nwp_form(
        page,
        name="SQA Holiday Closure",
        description="SQA updated outage",
        start_dt="2026-05-21T06:00",
        days="0",
        hours="12",
    )
    await _submit_dialog(page)

    updated_row = page.locator("tr").filter(has_text="SQA Holiday Closure")
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.get_by_text("2026-05-21 06:00", exact=True)).to_be_visible(timeout=8_000)
    await expect(updated_row.get_by_text("12h", exact=True)).to_be_visible(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    period = _find_period(data, "SQA Holiday Closure")
    assert period is not None
    assert period["description"] == "SQA updated outage"
    assert period["start_datetime"].startswith("2026-05-21T06:00:00")
    assert period["duration_seconds"] == 43200


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_nwp_cleanup")
async def test_work_schedule_non_working_period_delete(page: Page, api) -> None:
    schedule = _create_schedule(api, "SQA NWP Schedule", "SQA non-working schedule")
    created = _create_period(api, schedule["id"], "SQA Plant Shutdown", "SQA planned outage", "2026-05-20T00:00:00", 86400)

    await _open_schedule_detail(page, schedule["id"])
    await _open_non_working_tab(page)

    row = page.locator("tr").filter(has_text="SQA Plant Shutdown")
    await expect(row).to_be_visible(timeout=8_000)

    async def _accept_dialog(dialog) -> None:
        await dialog.accept()

    page.once("dialog", _accept_dialog)
    await row.locator("button").nth(1).click()
    await expect(page.locator("tr").filter(has_text="SQA Plant Shutdown")).to_be_hidden(timeout=8_000)

    resp = api.get(f"{API_WORK_SCHEDULE}/{schedule['id']}/non-working-periods")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json().get("data", [])}
    assert created["id"] not in ids
