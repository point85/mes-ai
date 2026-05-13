"""
SQA-DT — Work Schedule rotation CRUD editor tests.

Surfaces: DT-CLIENT /work-schedules/:id detail page (Rotations tab)
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


def _delete_schedule_if_present(api, name: str) -> None:
    found = _find_schedule_by_name(api, name)
    if found is not None:
        api.delete(f"{API_WORK_SCHEDULE}/{found['id']}")


@pytest.fixture
def work_schedule_rotation_cleanup(api):
    _delete_schedule_if_present(api, "SQA Rotation Schedule")
    yield
    _delete_schedule_if_present(api, "SQA Rotation Schedule")


async def _open_schedule_detail(page: Page, schedule_id: str) -> None:
    await page.goto(f"{DT_WORK_SCHEDULE_URL}/{schedule_id}")
    await expect(page.get_by_role("button", name="Rotations")).to_be_visible(timeout=10_000)


async def _open_rotations_tab(page: Page) -> None:
    await page.get_by_role("button", name="Rotations").click()
    await expect(page.get_by_role("button", name="New Rotation")).to_be_visible(timeout=8_000)


async def _fill_rotation_form(page: Page, *, name: str, description: str) -> None:
    await page.locator("label:has-text('Name *') + input").fill(name)
    await page.locator("label:has-text('Description') + input").fill(description)


async def _submit_dialog(page: Page) -> None:
    await page.locator("button[type='submit']").click()


def _rotation_card(page: Page, rotation_name: str):
    return page.locator("div.rounded-lg.border.border-gray-200.bg-white.shadow-sm").filter(has_text=rotation_name)


def _segment_row(rotation_card, shift_name: str):
    return rotation_card.locator("div.flex.items-center.gap-3.text-sm").filter(has_text=shift_name)


def _find_rotation(schedule_data: dict, name: str):
    return next((rotation for rotation in schedule_data.get("rotations", []) if rotation.get("name") == name), None)


def _find_segment(rotation_data: dict, shift_name: str):
    return next((segment for segment in rotation_data.get("segments", []) if segment.get("shift_name") == shift_name), None)


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_rotation_cleanup")
async def test_work_schedule_rotation_create(page: Page, api) -> None:
    schedule = _create_schedule(api, "SQA Rotation Schedule", "SQA rotation schedule")

    await _open_schedule_detail(page, schedule["id"])
    await _open_rotations_tab(page)

    await page.get_by_role("button", name="New Rotation").click()
    await expect(page.get_by_role("heading", name="New Rotation")).to_be_visible(timeout=5_000)
    await _fill_rotation_form(page, name="SQA Rotation A", description="SQA first rotation")
    await _submit_dialog(page)

    rotation_card = _rotation_card(page, "SQA Rotation A")
    await expect(rotation_card).to_be_visible(timeout=8_000)
    await expect(rotation_card.get_by_text("0 days", exact=True)).to_be_visible(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    rotation = _find_rotation(data, "SQA Rotation A")
    assert rotation is not None
    assert rotation["description"] == "SQA first rotation"
    assert rotation["segments"] == []


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_rotation_cleanup")
async def test_work_schedule_rotation_edit(page: Page, api) -> None:
    schedule = _create_schedule(api, "SQA Rotation Schedule", "SQA rotation schedule")
    _create_rotation(api, schedule["id"], "SQA Rotation A", "SQA first rotation")

    await _open_schedule_detail(page, schedule["id"])
    await _open_rotations_tab(page)

    rotation_card = _rotation_card(page, "SQA Rotation A")
    await expect(rotation_card).to_be_visible(timeout=8_000)
    await rotation_card.locator("button").nth(1).click()
    await expect(page.get_by_role("heading", name="Edit Rotation")).to_be_visible(timeout=5_000)
    await _fill_rotation_form(page, name="SQA Rotation B", description="SQA updated rotation")
    await _submit_dialog(page)

    updated_card = _rotation_card(page, "SQA Rotation B")
    await expect(updated_card).to_be_visible(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    rotation = _find_rotation(data, "SQA Rotation B")
    assert rotation is not None
    assert rotation["description"] == "SQA updated rotation"


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_rotation_cleanup")
async def test_work_schedule_rotation_delete(page: Page, api) -> None:
    schedule = _create_schedule(api, "SQA Rotation Schedule", "SQA rotation schedule")
    _create_rotation(api, schedule["id"], "SQA Rotation A", "SQA first rotation")

    await _open_schedule_detail(page, schedule["id"])
    await _open_rotations_tab(page)

    rotation_card = _rotation_card(page, "SQA Rotation A")
    await expect(rotation_card).to_be_visible(timeout=8_000)

    async def _accept_dialog(dialog) -> None:
        await dialog.accept()

    page.once("dialog", _accept_dialog)
    await rotation_card.locator("button").nth(2).click()

    await expect(_rotation_card(page, "SQA Rotation A")).to_be_hidden(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert _find_rotation(data, "SQA Rotation A") is None


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_rotation_cleanup")
async def test_work_schedule_rotation_add_segment(page: Page, api) -> None:
    schedule = _create_schedule(api, "SQA Rotation Schedule", "SQA rotation schedule")
    shift = _create_shift(api, schedule["id"], "SQA Day Shift", "SQA shift", "06:00:00", 28800)
    _create_rotation(api, schedule["id"], "SQA Rotation A", "SQA first rotation")

    await _open_schedule_detail(page, schedule["id"])
    await _open_rotations_tab(page)

    rotation_card = _rotation_card(page, "SQA Rotation A")
    await expect(rotation_card).to_be_visible(timeout=8_000)
    await rotation_card.locator("button").nth(0).click()
    await rotation_card.get_by_role("button", name="Add Segment").click()
    await expect(page.get_by_role("heading", name="Add Rotation Segment")).to_be_visible(timeout=5_000)

    await page.locator("label:has-text('Shift *') + select").select_option(value=shift["id"])
    await page.locator("label:has-text('Days On') + input").fill("5")
    await page.locator("label:has-text('Days Off') + input").fill("2")
    await page.locator("label:has-text('Sequence') + input").fill("1")
    await _submit_dialog(page)

    segment = _segment_row(rotation_card, "SQA Day Shift")
    await expect(segment).to_be_visible(timeout=8_000)
    await expect(segment.get_by_text("#1", exact=True)).to_be_visible(timeout=8_000)
    await expect(segment.get_by_text("5 on / 2 off", exact=True)).to_be_visible(timeout=8_000)
    await expect(rotation_card.get_by_text("7 days", exact=True)).to_be_visible(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    rotation = _find_rotation(data, "SQA Rotation A")
    assert rotation is not None
    seg = _find_segment(rotation, "SQA Day Shift")
    assert seg is not None
    assert seg["days_on"] == 5
    assert seg["days_off"] == 2
    assert seg["sequence"] == 1

    await segment.locator("button").click()
    await expect(_segment_row(rotation_card, "SQA Day Shift")).to_be_hidden(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    rotation = _find_rotation(data, "SQA Rotation A")
    assert rotation is not None
    assert _find_segment(rotation, "SQA Day Shift") is None