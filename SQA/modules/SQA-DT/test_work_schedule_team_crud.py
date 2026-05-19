"""
SQA-DT — Work Schedule team CRUD editor tests.

Surfaces: DT-CLIENT /work-schedules/:id detail page (Teams tab)
          + MES REST API /api/v1/work-schedules and /api/v1/auth/users
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from playwright.async_api import Page, expect

import os
_DT_BASE = os.environ.get("SQA_DT_URL", "http://localhost:5177")
DT_WORK_SCHEDULE_URL = f"{_DT_BASE}/work-schedules"
API_WORK_SCHEDULE = "/work-schedules"
API_USERS = "/auth/users"


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


def _list_users(api):
    return api.get(API_USERS)


def _find_user_by_username(api, username: str):
    resp = _list_users(api)
    assert resp.status_code == 200, f"List users failed: {resp.text}"
    users = resp.json().get("data", [])
    return next((user for user in users if user.get("username") == username), None)


def _create_user(api, username: str, full_name: str):
    resp = api.post(
        API_USERS,
        json={
            "username": username,
            "full_name": full_name,
            "password": "SqaPass123!",
        },
    )
    assert resp.status_code in (200, 201), f"Create user failed ({username}): {resp.text}"
    return resp.json()["data"]


def _delete_user_if_present(api, username: str) -> None:
    user = _find_user_by_username(api, username)
    if user is not None:
        api.delete(f"{API_USERS}/{user['id']}")


def _delete_schedule_if_present(api, name: str) -> None:
    found = _find_schedule_by_name(api, name)
    if found is not None:
        api.delete(f"{API_WORK_SCHEDULE}/{found['id']}")


@pytest.fixture
def work_schedule_team_cleanup(api):
    _delete_schedule_if_present(api, "SQA Team Schedule")
    yield
    _delete_schedule_if_present(api, "SQA Team Schedule")


async def _open_schedule_detail(page: Page, schedule_id: str) -> None:
    await page.goto(f"{DT_WORK_SCHEDULE_URL}/{schedule_id}")
    await expect(page.get_by_role("button", name="Teams")).to_be_visible(timeout=10_000)


async def _open_teams_tab(page: Page) -> None:
    await page.get_by_role("button", name="Teams").click()
    await expect(page.get_by_role("button", name="New Team")).to_be_visible(timeout=8_000)


async def _fill_team_form(page: Page, *, name: str, description: str, rotation_id: str, rotation_start: str) -> None:
    await page.locator("label:has-text('Name *') + input").fill(name)
    await page.locator("label:has-text('Description') + input").fill(description)
    await page.locator("label:has-text('Rotation *') + select").select_option(value=rotation_id)
    await page.locator("label:has-text('Rotation Start Date *') + input").fill(rotation_start)


async def _submit_dialog(page: Page) -> None:
    await page.locator("button[type='submit']").click()


def _team_card(page: Page, team_name: str):
    return page.locator("div.rounded-lg.border.border-gray-200.bg-white.shadow-sm").filter(has_text=team_name)


def _member_row(team_card, member_name: str):
    return team_card.locator("div.flex.items-center.gap-3.text-sm").filter(has_text=member_name)


def _find_team(schedule_data: dict, name: str):
    return next((team for team in schedule_data.get("teams", []) if team.get("name") == name), None)


def _find_member(team_data: dict, member_id: str):
    return next((member for member in team_data.get("members", []) if member.get("member_id") == member_id), None)


def _seed_schedule_with_rotation(api):
    schedule = _create_schedule(api, "SQA Team Schedule", "SQA team schedule")
    shift = _create_shift(api, schedule["id"], "SQA Day Shift", "SQA shift", "06:00:00", 28800)
    rotation = _create_rotation(api, schedule["id"], "SQA Rotation A", "SQA rotation")
    _create_rotation_segment(api, schedule["id"], rotation["id"], shift["id"], 5, 2, 1)
    return schedule, rotation


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_team_cleanup")
async def test_work_schedule_team_create(page: Page, api) -> None:
    schedule, rotation = _seed_schedule_with_rotation(api)

    await _open_schedule_detail(page, schedule["id"])
    await _open_teams_tab(page)

    await page.get_by_role("button", name="New Team").click()
    await expect(page.get_by_role("heading", name="New Team")).to_be_visible(timeout=5_000)
    await _fill_team_form(
        page,
        name="SQA Team A",
        description="SQA first team",
        rotation_id=rotation["id"],
        rotation_start="2026-05-13",
    )
    await _submit_dialog(page)

    team_card = _team_card(page, "SQA Team A")
    await expect(team_card).to_be_visible(timeout=8_000)
    await expect(team_card.get_by_text("starts 2026-05-13", exact=True)).to_be_visible(timeout=8_000)
    await expect(team_card.get_by_text("0 members", exact=True)).to_be_visible(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    team = _find_team(data, "SQA Team A")
    assert team is not None
    assert team["description"] == "SQA first team"
    assert team["rotation_id"] == rotation["id"]
    assert team["rotation_start"] == "2026-05-13"


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_team_cleanup")
async def test_work_schedule_team_edit(page: Page, api) -> None:
    schedule, rotation = _seed_schedule_with_rotation(api)
    api.post(
        f"{API_WORK_SCHEDULE}/{schedule['id']}/teams",
        json={
            "name": "SQA Team A",
            "description": "SQA first team",
            "rotation_id": rotation["id"],
            "rotation_start": "2026-05-13",
        },
    )

    await _open_schedule_detail(page, schedule["id"])
    await _open_teams_tab(page)

    team_card = _team_card(page, "SQA Team A")
    await expect(team_card).to_be_visible(timeout=8_000)
    await team_card.locator("button").nth(1).click()
    await expect(page.get_by_role("heading", name="Edit Team")).to_be_visible(timeout=5_000)
    await _fill_team_form(
        page,
        name="SQA Team B",
        description="SQA updated team",
        rotation_id=rotation["id"],
        rotation_start="2026-05-20",
    )
    await _submit_dialog(page)

    updated_card = _team_card(page, "SQA Team B")
    await expect(updated_card).to_be_visible(timeout=8_000)
    await expect(updated_card.get_by_text("starts 2026-05-20", exact=True)).to_be_visible(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    team = _find_team(data, "SQA Team B")
    assert team is not None
    assert team["description"] == "SQA updated team"
    assert team["rotation_start"] == "2026-05-20"


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_team_cleanup")
async def test_work_schedule_team_delete(page: Page, api) -> None:
    schedule, rotation = _seed_schedule_with_rotation(api)
    api.post(
        f"{API_WORK_SCHEDULE}/{schedule['id']}/teams",
        json={
            "name": "SQA Team A",
            "description": "SQA first team",
            "rotation_id": rotation["id"],
            "rotation_start": "2026-05-13",
        },
    )

    await _open_schedule_detail(page, schedule["id"])
    await _open_teams_tab(page)

    team_card = _team_card(page, "SQA Team A")
    await expect(team_card).to_be_visible(timeout=8_000)

    async def _accept_dialog(dialog) -> None:
        await dialog.accept()

    page.once("dialog", _accept_dialog)
    await team_card.locator("button").nth(2).click()

    await expect(_team_card(page, "SQA Team A")).to_be_hidden(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert _find_team(data, "SQA Team A") is None


@pytest.mark.ui
@pytest.mark.usefixtures("work_schedule_team_cleanup")
async def test_work_schedule_team_add_member(page: Page, api) -> None:
    schedule, rotation = _seed_schedule_with_rotation(api)
    api.post(
        f"{API_WORK_SCHEDULE}/{schedule['id']}/teams",
        json={
            "name": "SQA Team A",
            "description": "SQA first team",
            "rotation_id": rotation["id"],
            "rotation_start": "2026-05-13",
        },
    )
    username = f"sqa-team-user-{uuid4().hex[:8]}"
    _create_user(api, username, "SQA Team User")

    await _open_schedule_detail(page, schedule["id"])
    await _open_teams_tab(page)

    team_card = _team_card(page, "SQA Team A")
    await expect(team_card).to_be_visible(timeout=8_000)
    await team_card.locator("button").nth(0).click()
    await team_card.get_by_role("button", name="Add Member").click()
    await expect(page.get_by_role("heading", name="Add Member")).to_be_visible(timeout=5_000)

    await page.locator("label:has-text('Username') + input").fill(username)
    await _submit_dialog(page)

    member = _member_row(team_card, "SQA Team User")
    await expect(member).to_be_visible(timeout=8_000)
    await expect(member.get_by_text(username, exact=True)).to_be_visible(timeout=8_000)
    await expect(team_card.get_by_text("1 member", exact=True)).to_be_visible(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    team = _find_team(data, "SQA Team A")
    assert team is not None
    added = _find_member(team, username)
    assert added is not None
    assert added["name"] == "SQA Team User"

    await member.locator("button").click()
    await expect(_member_row(team_card, "SQA Team User")).to_be_hidden(timeout=8_000)

    resp = _get_schedule(api, schedule["id"])
    assert resp.status_code == 200
    data = resp.json()["data"]
    team = _find_team(data, "SQA Team A")
    assert team is not None
    assert _find_member(team, username) is None