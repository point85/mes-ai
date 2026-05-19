"""
SQA-DT -- Auth admin CRUD tests for users and roles (user groups).

Surfaces:
- DT-CLIENT /admin/users page
- DT-CLIENT /admin/roles page
- MES REST API /api/v1/auth/users
- MES REST API /api/v1/auth/roles

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
DT_USERS_URL = f"{_DT_BASE}/admin/users"
DT_ROLES_URL = f"{_DT_BASE}/admin/roles"
API_USERS = "/auth/users"
API_ROLES = "/auth/roles"


def _unique_username() -> str:
    return f"sqa-auth-user-{uuid4().hex[:8]}"


def _unique_role_name() -> str:
    return f"SQA_ROLE_{uuid4().hex[:8].upper()}"


def _list_users(api) -> list[dict]:
    resp = api.get(API_USERS)
    assert resp.status_code == 200, f"List users failed: {resp.text}"
    return resp.json().get("data", [])


def _find_user_by_username(api, username: str) -> dict | None:
    return next((item for item in _list_users(api) if item.get("username") == username), None)


def _create_user(api, *, username: str, full_name: str, email: str | None = None) -> dict:
    payload = {
        "username": username,
        "full_name": full_name,
        "email": email,
        "password": "SqaPass123!",
    }
    resp = api.post(API_USERS, json=payload)
    assert resp.status_code in (200, 201), f"Create user failed ({username}): {resp.text}"
    return resp.json()["data"]


def _list_roles(api) -> list[dict]:
    resp = api.get(API_ROLES)
    assert resp.status_code == 200, f"List roles failed: {resp.text}"
    return resp.json().get("data", [])


def _find_role_by_name(api, role_name: str) -> dict | None:
    return next((item for item in _list_roles(api) if item.get("name") == role_name), None)


def _create_role(api, *, name: str, description: str | None = None) -> dict:
    resp = api.post(API_ROLES, json={"name": name, "description": description})
    assert resp.status_code in (200, 201), f"Create role failed ({name}): {resp.text}"
    return resp.json()["data"]


async def _open_users_page(page: Page) -> None:
    await page.goto(DT_USERS_URL)
    await expect(page.get_by_role("heading", name="Users")).to_be_visible(timeout=10_000)


async def _open_roles_page(page: Page) -> None:
    await page.goto(DT_ROLES_URL)
    await expect(page.get_by_role("heading", name="Roles")).to_be_visible(timeout=10_000)


async def _fill_user_form(
    page: Page,
    *,
    username: str | None = None,
    email: str,
    full_name: str,
    password: str | None = None,
    is_active: bool | None = None,
    role_names: list[str] | None = None,
) -> None:
    if username is not None:
        await page.locator("label:has-text('Username') + input").fill(username)
    await page.locator("label:has-text('Email') + input").fill(email)
    await page.locator("label:has-text('Full Name') + input").fill(full_name)
    if password is not None:
        await page.locator("input[type='password']").fill(password)

    if is_active is not None:
        is_active_checkbox = page.locator("input#is-active")
        if await is_active_checkbox.is_checked() != is_active:
            await is_active_checkbox.click()

    if role_names is not None:
        for role_name in role_names:
            role_checkbox = page.locator("label", has_text=role_name).locator("input[type='checkbox']")
            if not await role_checkbox.is_checked():
                await role_checkbox.click()


async def _submit_dialog(page: Page) -> None:
    await page.locator("button[type='submit']").click()


@pytest.mark.ui
@pytest.mark.usefixtures("auth_admin_cleanup")
async def test_role_create(page: Page, api) -> None:
    role_name = _unique_role_name()

    await _open_roles_page(page)
    await page.get_by_role("button", name="New Role").click()
    await expect(page.get_by_role("heading", name="New Role")).to_be_visible(timeout=5_000)

    await page.locator("label:has-text('Name') + input").fill(role_name)
    await page.locator("label:has-text('Description') + input").fill("SQA role create path")
    await _submit_dialog(page)

    row = page.locator("tr").filter(has_text=role_name)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row).to_contain_text("SQA role create path")
    await expect(row).to_contain_text("0 permission")

    created = _find_role_by_name(api, role_name)
    assert created is not None
    assert created["description"] == "SQA role create path"
    assert created["is_system"] is False
    assert created["permissions"] == []


@pytest.mark.ui
@pytest.mark.usefixtures("auth_admin_cleanup")
async def test_role_edit_permissions(page: Page, api) -> None:
    role_name = _unique_role_name()
    role = _create_role(api, name=role_name, description="SQA role edit path")

    await _open_roles_page(page)

    row = page.locator("tr").filter(has_text=role_name)
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("View / Edit").click()
    await expect(page.get_by_role("heading", name=f"Edit Role — {role_name}")).to_be_visible(timeout=5_000)

    perm_input = page.get_by_placeholder("e.g. module.resource.action")
    await perm_input.fill("sqa.auth.users.manage")
    await page.get_by_role("button", name="Add").click()
    await _submit_dialog(page)

    updated_row = page.locator("tr").filter(has_text=role_name)
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row).to_contain_text("1 permission")

    updated = _find_role_by_name(api, role_name)
    assert updated is not None
    assert "sqa.auth.users.manage" in updated["permissions"]


@pytest.mark.ui
@pytest.mark.usefixtures("auth_admin_cleanup")
async def test_role_delete(page: Page, api) -> None:
    role_name = _unique_role_name()
    role = _create_role(api, name=role_name, description="SQA role delete path")

    await _open_roles_page(page)

    row = page.locator("tr").filter(has_text=role_name)
    await expect(row).to_be_visible(timeout=8_000)
    page.once("dialog", lambda dialog: dialog.accept())
    await row.get_by_title("Delete").click()

    await expect(page.locator("td", has_text=role_name)).to_be_hidden(timeout=8_000)
    assert _find_role_by_name(api, role_name) is None


@pytest.mark.ui
@pytest.mark.usefixtures("auth_admin_cleanup")
async def test_user_create_with_role(page: Page, api) -> None:
    role_name = _unique_role_name()
    _create_role(api, name=role_name, description="SQA user role")
    username = _unique_username()

    await _open_users_page(page)
    await page.get_by_role("button", name="New User").click()
    await expect(page.get_by_role("heading", name="New User")).to_be_visible(timeout=5_000)

    await _fill_user_form(
        page,
        username=username,
        email="sqa.auth@example.com",
        full_name="SQA Auth User",
        password="SqaPass123!",
        role_names=[role_name],
    )
    await _submit_dialog(page)

    row = page.locator("tr").filter(has_text=username)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row).to_contain_text("SQA Auth User")
    await expect(row).to_contain_text("sqa.auth@example.com")
    await expect(row).to_contain_text(role_name)

    created = _find_user_by_username(api, username)
    assert created is not None
    assert created["full_name"] == "SQA Auth User"
    assert created["email"] == "sqa.auth@example.com"
    assert role_name in created["roles"]


@pytest.mark.ui
@pytest.mark.usefixtures("auth_admin_cleanup")
async def test_user_edit(page: Page, api) -> None:
    username = _unique_username()
    user = _create_user(api, username=username, full_name="SQA Editable User", email="before@example.com")

    await _open_users_page(page)

    row = page.locator("tr").filter(has_text=username)
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name=f"Edit User — {username}")).to_be_visible(timeout=5_000)

    await _fill_user_form(
        page,
        email="after@example.com",
        full_name="SQA Edited User",
    )
    await _submit_dialog(page)

    updated_row = page.locator("tr").filter(has_text=username)
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row).to_contain_text("SQA Edited User")
    await expect(updated_row).to_contain_text("after@example.com")

    resp = api.get(f"{API_USERS}/{user['id']}")
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]
    assert updated["email"] == "after@example.com"
    assert updated["full_name"] == "SQA Edited User"
    assert updated["is_active"] is True


@pytest.mark.ui
@pytest.mark.usefixtures("auth_admin_cleanup")
async def test_user_delete(page: Page, api) -> None:
    username = _unique_username()
    user = _create_user(api, username=username, full_name="SQA Delete User", email="delete@example.com")

    await _open_users_page(page)

    row = page.locator("tr").filter(has_text=username)
    await expect(row).to_be_visible(timeout=8_000)
    page.once("dialog", lambda dialog: dialog.accept())
    await row.get_by_title("Delete").click()

    await expect(page.locator("td", has_text=username)).to_be_hidden(timeout=8_000)

    resp = api.get(f"{API_USERS}/{user['id']}")
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}: {resp.text}"