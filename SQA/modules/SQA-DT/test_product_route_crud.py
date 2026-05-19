"""
SQA-DT -- Product detail route CRUD tests.

Surfaces:
- DT-CLIENT /products/:productId detail page
- MES REST API /api/v1/products/{productId}/operations-definitions
- MES REST API /api/v1/operations-definitions/{routeId}
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from playwright.async_api import Page, expect

import os
_DT_BASE = os.environ.get("SQA_DT_URL", "http://localhost:5177")

API_PRODUCTS = "/products"
API_UOM = "/uom"


def _unique_product_code() -> str:
    return f"SQA_PROD_{uuid4().hex[:8]}"


def _unique_uom_symbol() -> str:
    return f"SQA_RT_{uuid4().hex[:8]}"


def _create_scalar_uom(api, *, symbol: str, name: str) -> dict:
    resp = api.post(
        API_UOM,
        json={
            "symbol": symbol,
            "name": name,
            "uom_type": "count",
            "uom_class": "scalar",
            "multiplier": 1.0,
            "offset": 0.0,
        },
    )
    assert resp.status_code in (200, 201), f"UoM setup failed: {resp.text}"
    return resp.json()["data"]


def _create_product(api, *, uom_id: str) -> dict:
    resp = api.post(
        API_PRODUCTS,
        json={
            "code": _unique_product_code(),
            "name": "SQA Route Product",
            "version": "1.0",
            "description": "SQA product for route tests",
            "uom_id": uom_id,
            "product_type": "discrete",
        },
    )
    assert resp.status_code in (200, 201), f"Product setup failed: {resp.text}"
    return resp.json()["data"]


def _create_route(api, *, product_id: str, **overrides) -> dict:
    payload = {
        "name": "SQA Main Route",
        "version": "1.0",
        "description": "SQA route",
        "is_default": False,
    }
    payload.update(overrides)
    resp = api.post(f"{API_PRODUCTS}/{product_id}/operations-definitions", json=payload)
    assert resp.status_code in (200, 201), f"Route setup failed: {resp.text}"
    return resp.json()["data"]


async def _open_product_detail(page: Page, *, product_id: str) -> None:
    await page.goto(f"{_DT_BASE}/products/{product_id}")
    await expect(page.get_by_text("Process Routes")).to_be_visible(timeout=10_000)


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "uom_cleanup")
async def test_route_create_from_product_detail(page: Page, api) -> None:
    uom = _create_scalar_uom(api, symbol=_unique_uom_symbol(), name="SQA Route Each")
    product = _create_product(api, uom_id=uom["id"])

    await _open_product_detail(page, product_id=product["id"])
    await page.get_by_role("button", name="New Route").click()
    await expect(page.get_by_role("heading", name="New Process Route")).to_be_visible(timeout=5_000)

    await page.locator("input[name='name']").fill("SQA Route Alpha")
    await page.locator("input[name='version']").fill("2.0")
    await page.locator("textarea[name='description']").fill("SQA route create path")
    await page.locator("input[name='is_default']").check()
    await page.locator("button[type='submit']").click()

    route_row = page.locator("div").filter(has_text="SQA Route Alpha").filter(has_text="v2.0").first
    await expect(route_row).to_be_visible(timeout=8_000)
    await expect(route_row.get_by_text("default")).to_be_visible()

    resp = api.get(f"{API_PRODUCTS}/{product['id']}/operations-definitions", params={"limit": "200"})
    assert resp.status_code == 200, resp.text
    created = next((item for item in resp.json()["data"] if item["name"] == "SQA Route Alpha"), None)
    assert created is not None
    assert created["version"] == "2.0"
    assert created["is_default"] is True


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "uom_cleanup")
async def test_route_edit_from_product_detail(page: Page, api) -> None:
    uom = _create_scalar_uom(api, symbol=_unique_uom_symbol(), name="SQA Route Each")
    product = _create_product(api, uom_id=uom["id"])
    route = _create_route(api, product_id=product["id"], name="SQA Route Beta", version="1.0", is_default=False)

    await _open_product_detail(page, product_id=product["id"])

    route_row = page.locator("div").filter(has_text="SQA Route Beta").filter(has_text="v1.0").first
    await expect(route_row).to_be_visible(timeout=8_000)
    await route_row.get_by_title("Edit route").click()
    await expect(page.get_by_role("heading", name="Edit Process Route")).to_be_visible(timeout=5_000)

    await page.locator("input[name='name']").fill("SQA Route Gamma")
    await page.locator("input[name='version']").fill("1.1")
    await page.locator("input[name='is_default']").check()
    await page.locator("button[type='submit']").click()

    updated_row = page.locator("div").filter(has_text="SQA Route Gamma").filter(has_text="v1.1").first
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.get_by_text("default")).to_be_visible()

    resp = api.get(f"/operations-definitions/{route['id']}")
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]
    assert updated["name"] == "SQA Route Gamma"
    assert updated["version"] == "1.1"
    assert updated["is_default"] is True


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "uom_cleanup")
async def test_route_delete_from_product_detail(page: Page, api) -> None:
    uom = _create_scalar_uom(api, symbol=_unique_uom_symbol(), name="SQA Route Each")
    product = _create_product(api, uom_id=uom["id"])
    route = _create_route(api, product_id=product["id"], name="SQA Route Delete", version="7.0")

    await _open_product_detail(page, product_id=product["id"])

    route_row = page.locator("div").filter(has_text="SQA Route Delete").filter(has_text="v7.0").first
    await expect(route_row).to_be_visible(timeout=8_000)

    page.on("dialog", lambda dialog: dialog.accept())
    await route_row.get_by_title("Delete route").click()

    await expect(page.get_by_text("SQA Route Delete")).to_be_hidden(timeout=8_000)

    resp = api.get(f"/operations-definitions/{route['id']}")
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}: {resp.text}"