"""
SQA-DT -- Product CRUD, filter, and detail navigation tests.

Surfaces:
- DT-CLIENT /products page
- DT-CLIENT /products/:productId detail page
- MES REST API /api/v1/products

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
DT_PRODUCTS_URL = f"{_DT_BASE}/products"
API_PRODUCTS = "/products"
API_UOM = "/uom"


def _unique_product_code(prefix: str = "SQA_PROD") -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _unique_uom_symbol(prefix: str = "SQA_PU") -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _create_scalar_uom(api, *, symbol: str, name: str, uom_type: str = "count") -> dict:
    resp = api.post(
        API_UOM,
        json={
            "symbol": symbol,
            "name": name,
            "uom_type": uom_type,
            "uom_class": "scalar",
            "multiplier": 1.0,
            "offset": 0.0,
        },
    )
    assert resp.status_code in (200, 201), f"UoM setup failed: {resp.text}"
    return resp.json()["data"]


def _create_product(api, **overrides) -> dict:
    uom = _create_scalar_uom(
        api,
        symbol=_unique_uom_symbol(),
        name="SQA Product Count",
    )
    payload = {
        "code": _unique_product_code(),
        "name": "SQA Product",
        "version": "1.0",
        "description": "SQA seeded product",
        "uom_id": uom["id"],
        "product_type": "discrete",
    }
    payload.update(overrides)
    resp = api.post(API_PRODUCTS, json=payload)
    assert resp.status_code in (200, 201), f"Product setup failed: {resp.text}"
    return resp.json()["data"]


async def _open_products_page(page: Page) -> None:
    await page.goto(DT_PRODUCTS_URL)
    await expect(page.get_by_role("heading", name="Products")).to_be_visible(timeout=10_000)


async def _open_new_product_dialog(page: Page) -> None:
    await page.get_by_role("button", name="New Product").click()
    await expect(page.get_by_role("heading", name="New Product")).to_be_visible(timeout=5_000)


async def _fill_product_form(
    page: Page,
    *,
    code: str,
    name: str,
    version: str,
    uom_id: str,
    product_type: str = "discrete",
    description: str | None = None,
) -> None:
    await page.locator("input[name='code']").fill(code)
    await page.locator("input[name='version']").fill(version)
    await page.locator("input[name='name']").fill(name)
    await page.locator("select[name='product_type']").select_option(value=product_type)
    await page.locator("select[name='uom_id']").select_option(value=uom_id)
    if description is not None:
        await page.locator("textarea[name='description']").fill(description)


async def _submit_dialog(page: Page) -> None:
    await page.locator("button[type='submit']").click()


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "uom_cleanup")
async def test_product_create(page: Page, api) -> None:
    code = _unique_product_code()
    name = "SQA Widget Assembly"
    uom = _create_scalar_uom(
        api,
        symbol=_unique_uom_symbol(),
        name="SQA Product Each",
    )

    await _open_products_page(page)
    await _open_new_product_dialog(page)
    await _fill_product_form(
        page,
        code=code,
        name=name,
        version="1.0",
        uom_id=uom["id"],
        product_type="discrete",
        description="SQA product create path",
    )
    await _submit_dialog(page)

    row = page.locator("tr").filter(has_text=code)
    await expect(row).to_be_visible(timeout=8_000)
    await expect(row.locator("td", has_text=name)).to_be_visible()

    resp = api.get(API_PRODUCTS, params={"limit": "200"})
    assert resp.status_code == 200, resp.text
    items = resp.json()["data"]
    created = next((item for item in items if item["code"] == code), None)
    assert created is not None
    assert created["name"] == name
    assert created["version"] == "1.0"
    assert created["product_type"] == "discrete"
    assert created["uom_id"] == uom["id"]


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "uom_cleanup")
async def test_product_edit(page: Page, api) -> None:
    original_uom = _create_scalar_uom(
        api,
        symbol=_unique_uom_symbol(),
        name="SQA Original Each",
    )
    updated_uom = _create_scalar_uom(
        api,
        symbol=_unique_uom_symbol(),
        name="SQA Updated Kilogram",
        uom_type="mass",
    )
    product = _create_product(
        api,
        code=_unique_product_code(),
        name="SQA Editable Product",
        version="1.0",
        uom_id=original_uom["id"],
        product_type="discrete",
    )

    await _open_products_page(page)

    row = page.locator("tr").filter(has_text=product["code"])
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_title("Edit").click()
    await expect(page.get_by_role("heading", name="Edit Product")).to_be_visible(timeout=5_000)

    await _fill_product_form(
        page,
        code=product["code"],
        name="SQA Edited Product",
        version="2.0",
        uom_id=updated_uom["id"],
        product_type="configurable",
        description="SQA edited product path",
    )
    await _submit_dialog(page)

    updated_row = page.locator("tr").filter(has_text=product["code"])
    await expect(updated_row).to_be_visible(timeout=8_000)
    await expect(updated_row.locator("td", has_text="SQA Edited Product")).to_be_visible()
    await expect(updated_row.locator("td", has_text="2.0")).to_be_visible()

    resp = api.get(f"{API_PRODUCTS}/{product['id']}")
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]
    assert updated["name"] == "SQA Edited Product"
    assert updated["version"] == "2.0"
    assert updated["product_type"] == "configurable"
    assert updated["uom_id"] == updated_uom["id"]


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "uom_cleanup")
async def test_product_delete(page: Page, api) -> None:
    product = _create_product(api, code=_unique_product_code(), name="SQA Delete Product")

    await _open_products_page(page)

    row = page.locator("tr").filter(has_text=product["code"])
    await expect(row).to_be_visible(timeout=8_000)

    page.on("dialog", lambda dialog: dialog.accept())
    await row.get_by_title("Delete").click()

    await expect(page.locator("td", has_text=product["code"])).to_be_hidden(timeout=8_000)

    resp = api.get(f"{API_PRODUCTS}/{product['id']}")
    assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}: {resp.text}"


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "uom_cleanup")
async def test_product_filter(page: Page, api) -> None:
    discrete_code = _unique_product_code("SQA_PROD_DISCRETE")
    process_code = _unique_product_code("SQA_PROD_PROCESS")
    _create_product(api, code=discrete_code, name="SQA Discrete Product", product_type="discrete")
    _create_product(api, code=process_code, name="SQA Process Product", product_type="process")

    await _open_products_page(page)

    filter_select = page.locator("label:has-text('Filter by type:') + select")

    await filter_select.select_option(value="process")
    await expect(page.locator("td", has_text=process_code).first).to_be_visible(timeout=5_000)
    await expect(page.locator("td", has_text=discrete_code)).to_be_hidden()

    await filter_select.select_option(value="discrete")
    await expect(page.locator("td", has_text=discrete_code).first).to_be_visible(timeout=5_000)
    await expect(page.locator("td", has_text=process_code)).to_be_hidden()

    await filter_select.select_option(value="")
    await expect(page.locator("td", has_text=discrete_code).first).to_be_visible(timeout=5_000)
    await expect(page.locator("td", has_text=process_code).first).to_be_visible(timeout=5_000)


@pytest.mark.ui
@pytest.mark.usefixtures("product_cleanup", "uom_cleanup")
async def test_product_open_detail(page: Page, api) -> None:
    product = _create_product(api, code=_unique_product_code(), name="SQA Detail Product", version="3.1")

    await _open_products_page(page)

    row = page.locator("tr").filter(has_text=product["code"])
    await expect(row).to_be_visible(timeout=8_000)
    await row.get_by_role("link", name=product["code"]).click()

    await expect(page).to_have_url(f"{_DT_BASE}/products/{product['id']}")
    await expect(page.get_by_role("heading", name="SQA Detail Product")).to_be_visible(timeout=8_000)
    await expect(page.get_by_text(f"{product['code']} · v3.1", exact=False)).to_be_visible(timeout=8_000)
