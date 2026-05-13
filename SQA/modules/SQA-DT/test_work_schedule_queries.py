"""
SQA-DT — Work Schedule shift instances / working-time query tests.

Surfaces: DT-CLIENT Shift Instances dialog + MES REST query endpoints.
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


def _create_rotation(api, schedule_id: str, name: str, description: str | None):
    resp = api.post(
        f"{API_WORK_SCHEDULE}/{schedule_id}/rotations",
        json={"name": name, "description": description},
    )
    assert resp.status_code in (200, 201), f"Create rotation failed ({name}): {resp.text}"
    return resp.json()["data"]


def _create_rotation_segment(api, schedule_id: str, rotation_id: str, shift_id: str, days_on: int, days_off: int, sequence: int):
    resp = api.post(
        f"{API_WORK_SCHEDULE}/{schedule_id}/rotations/{rotation_id}/segments",
        json={
            "shift_id": shift_id,
            "days_on": days_on,
            "days_off": days_off,
            "sequence": sequence,
        },
    )
    assert resp.status_code in (200, 201), f"Create rotation segment failed: {resp.text}"
    return resp.json()["data"]


def _create_team(api, schedule_id: str, name: str, description: str | None, rotation_id: str, rotation_start: str):
    resp = api.post(
        f"{API_WORK_SCHEDULE}/{schedule_id}/teams",
        json={
            "name": name,
            "description": description,
            "rotation_id": rotation_id,
            "rotation_start": rotation_start,
        },
    )
    assert resp.status_code in (200, 201), f"Create team failed ({name}): {resp.text}"
    return resp.json()["data"]


def _delete_schedule_if_present(api, name: str) -> None:
    found = _find_schedule_by_name(api, name)
    if found is not None:
        api.delete(f"{API_WORK_SCHEDULE}/{found['id']}")


@pytest.fixture
def work_schedule_query_cleanup(api):
    _delete_schedule_if_present(api, "SQA Query Schedule")
    yield
    _delete_schedule_if_present(api, "SQA Query Schedule")


def _seed_schedule_for_queries(api):
    schedule = _create_schedule(api, "SQA Query Schedule", "SQA query schedule")
    shift = _create_shift(api, schedule["id"], "SQA Day Shift", "SQA shift", "06:00:00", 28800)
    rotation = _create_rotation(api, schedule["id"], "SQA Rotation A", "SQA rotation")
    _create_rotation_segment(api, schedule["id"], rotation["id"], shift["id"], 5, 2, 1)
    _create_team(api, schedule["id"], "SQA Team A", "SQA team", rotation["id"], "2026-05-13")
    return schedule


async def _open_shift_instances_dialog(page: Page, schedule_id: str) -> None:
    await page.goto(f"{DT_WORK_SCHEDULE_URL}/{schedule_id}")
    await expect(page.get_by_role("button", name="Shift Instances")).to_be_visible(timeout=10_000)
    await page.get_by_role("button", name="Shift Instances").click()
    await expect(page.get_by_role("heading").filter(has_text="Shift Instances")).to_be_visible(timeout=8_000)


def _fmt_seconds(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h} h {m} min"


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_query_cleanup")
async def test_work_schedule_shift_instances_query(page: Page, api) -> None:
    schedule = _seed_schedule_for_queries(api)

    from_dt = "2026-05-13T00:00"
    to_dt = "2026-05-14T00:00"

    range_resp = api.get(
        f"{API_WORK_SCHEDULE}/{schedule['id']}/shift-instances/range",
        params={"from_date": "2026-05-13", "to_date": "2026-05-14"},
    )
    assert range_resp.status_code == 200, range_resp.text
    instances = range_resp.json().get("data", [])
    assert any(item["shift_name"] == "SQA Day Shift" for item in instances)
    assert any(item["team_name"] == "SQA Team A" for item in instances)

    working_resp = api.get(
        f"{API_WORK_SCHEDULE}/{schedule['id']}/working-time",
        params={"from_dt": from_dt + ":00", "to_dt": to_dt + ":00"},
    )
    assert working_resp.status_code == 200, working_resp.text
    working_seconds = working_resp.json()["data"]["working_seconds"]

    await _open_shift_instances_dialog(page, schedule["id"])
    await page.locator("label:has-text('From') + input").fill(from_dt)
    await page.locator("label:has-text('To') + input").fill(to_dt)
    await page.get_by_role("button", name="Show Shifts").click()

    await expect(page.get_by_text(f"Working time: {_fmt_seconds(working_seconds)}", exact=True)).to_be_visible(timeout=8_000)
    await expect(page.get_by_role("cell", name="SQA Day Shift").first).to_be_visible(timeout=8_000)
    await expect(page.get_by_role("cell", name="SQA Team A").first).to_be_visible(timeout=8_000)


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_query_cleanup")
async def test_work_schedule_shift_instances_empty_state(page: Page, api) -> None:
    schedule = _seed_schedule_for_queries(api)

    await _open_shift_instances_dialog(page, schedule["id"])
    await page.locator("label:has-text('From') + input").fill("2026-06-01T00:00")
    await page.locator("label:has-text('To') + input").fill("2026-06-02T00:00")
    await page.get_by_role("button", name="Show Shifts").click()

    await expect(page.get_by_text("No shift instances in the selected period.", exact=True)).to_be_visible(timeout=8_000)
