"""
SQA-RT -- WIP lot flow test.

Flow covered:
- create a production order for FG-OJ-1L via the RT Orders page
- release the order
- create a lot for that order
- process the lot through the normal CPG route in RT Active WIP

The test uses existing seeded material lots for all required consumption.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re

import pytest
from playwright.async_api import Page, expect


API_PRODUCTS = "/products"
API_ORDERS = "/operations-requests"
API_UNITS = "/units"
API_LOTS = "/lots"
API_MATERIALS = "/materials"
API_MATERIAL_LOTS = "/material-lots"
SQA_ORDER_PREFIXES = ("SQA-WIP-", "SQA-MRB-", "SQA-ECB-")
SQA_UNIT_PREFIXES = ("SQA-ECB-SN-",)
SQA_LOT_PREFIXES = ("SQA-OJ-", "SQA-MRB-OJ-")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _unwrap(resp):
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _pick_numeric_value(item: dict) -> str:
    target = item.get("target_value")
    if target is not None:
      return str(target)

    lower = item.get("lower_limit")
    upper = item.get("upper_limit")
    if lower is not None and upper is not None:
      return str((float(lower) + float(upper)) / 2)
    if lower is not None:
      return str(lower)
    if upper is not None:
      return str(upper)
    return "1"


async def _open_orders(page: Page, rt_url: str) -> None:
    await page.goto(rt_url)
    await page.get_by_role("button", name="Orders").click()
    await expect(
        page.get_by_role("heading", name="Production Orders", exact=True)
    ).to_be_visible(timeout=10_000)


async def _open_active_lot(page: Page, lot_number: str) -> None:
    await page.get_by_role("button", name="WIP").click()
    await page.get_by_role("button", name="Active WIP").click()
    await expect(
        page.get_by_role("heading", name="Active WIP", exact=True)
    ).to_be_visible(timeout=10_000)

    await page.get_by_role("radio", name="Lots").check()
    status_select = page.locator("label:has-text('Status') ~ select:visible")
    await status_select.select_option("queued")

    lot_row = page.locator("tbody tr", has_text=lot_number).first
    await expect(lot_row).to_be_visible(timeout=15_000)
    await lot_row.get_by_role("button", name="Open").click()
    await expect(page.locator("h3.font-mono", has_text=lot_number)).to_be_visible(timeout=10_000)


async def _open_active_unit(page: Page, serial_number: str) -> None:
    await page.get_by_role("button", name="WIP").click()
    await page.get_by_role("button", name="Active WIP").click()
    await expect(
        page.get_by_role("heading", name="Active WIP", exact=True)
    ).to_be_visible(timeout=10_000)

    await page.get_by_role("radio", name="Units").check()
    status_select = page.locator("label:has-text('Status') ~ select:visible")
    await status_select.select_option("queued")

    unit_row = page.locator("tbody tr", has_text=serial_number).first
    await expect(unit_row).to_be_visible(timeout=15_000)
    await unit_row.get_by_role("button", name="Open").click()
    await expect(page.get_by_role("button", name="← Back to list")).to_be_visible(timeout=10_000)


async def _create_order_and_lot(page: Page, api, rt_url: str, product_id: str, order_number: str, lot_number: str) -> tuple[dict, dict]:
    await _open_orders(page, rt_url)

    await page.get_by_role("button", name="New").click()
    order_dialog_heading = page.get_by_role("heading", name="New Production Order")
    await expect(order_dialog_heading).to_be_visible(timeout=5_000)
    order_dialog = order_dialog_heading.locator("xpath=ancestor::div[contains(@class,'bg-white')][1]")
    await order_dialog.locator("label:has-text('Order Number') + input").fill(order_number)
    await order_dialog.locator("label:has-text('Product') + select").select_option(product_id)
    await order_dialog.locator("label:has-text('Quantity') + input").fill("1000")
    await order_dialog.locator("label:has-text('Priority') + input").fill("1")
    await order_dialog.get_by_role("button", name="Create Order").click()
    await expect(order_dialog_heading).to_be_hidden(timeout=10_000)

    order_row = page.locator("tbody tr", has_text=order_number).first
    await expect(order_row).to_be_visible(timeout=15_000)
    await order_row.click()
    await page.get_by_role("button", name="Release").click()
    await expect(order_row).to_contain_text(re.compile(r"released|in progress", re.IGNORECASE), timeout=10_000)

    await order_row.locator("button").first.click()
    await page.get_by_role("button", name="Create Lot").click()
    create_lot_panel = page.get_by_text("Create Lot", exact=True).locator("xpath=ancestor::div[contains(@class,'bg-indigo-50')][1]")
    await create_lot_panel.locator("label:has-text('Lot #') + input").fill(lot_number)
    await create_lot_panel.get_by_role("button", name="Create Lot").click()
    await expect(create_lot_panel.get_by_text(f"Lot {lot_number} created")).to_be_visible(timeout=10_000)

    orders = _unwrap(api.get(API_ORDERS, params={"limit": 200}))
    order = next((o for o in orders if o["order_number"] == order_number), None)
    assert order is not None, f"Order {order_number} not found after creation"
    assert order["status"] in {"released", "in_progress"}

    lots = _unwrap(api.get(API_LOTS, params={"order_id": order["id"], "limit": 200}))
    lot = next((item for item in lots if item["lot_number"] == lot_number), None)
    assert lot is not None, f"Lot {lot_number} not found after creation"
    return order, lot


async def _create_order_and_unit(page: Page, api, rt_url: str, product_id: str, order_number: str, serial_number: str) -> tuple[dict, dict]:
    await _open_orders(page, rt_url)

    await page.get_by_role("button", name="New").click()
    order_dialog_heading = page.get_by_role("heading", name="New Production Order")
    await expect(order_dialog_heading).to_be_visible(timeout=5_000)
    order_dialog = order_dialog_heading.locator("xpath=ancestor::div[contains(@class,'bg-white')][1]")
    await order_dialog.locator("label:has-text('Order Number') + input").fill(order_number)
    await order_dialog.locator("label:has-text('Product') + select").select_option(product_id)
    await order_dialog.locator("label:has-text('Quantity') + input").fill("1")
    await order_dialog.locator("label:has-text('Priority') + input").fill("1")
    await order_dialog.get_by_role("button", name="Create Order").click()
    await expect(order_dialog_heading).to_be_hidden(timeout=10_000)

    order_row = page.locator("tbody tr", has_text=order_number).first
    await expect(order_row).to_be_visible(timeout=15_000)
    await order_row.click()
    await page.get_by_role("button", name="Release").click()
    await expect(order_row).to_contain_text(re.compile(r"released|in progress", re.IGNORECASE), timeout=10_000)

    await order_row.locator("button").first.click()
    await page.get_by_role("button", name="Create Unit").click()
    create_unit_panel = page.get_by_text("Create Unit(s)", exact=True).locator("xpath=ancestor::div[contains(@class,'bg-indigo-50')][1]")
    await create_unit_panel.locator("label:has-text('How many') + input").fill("1")
    await create_unit_panel.locator("label:has-text('Serial #') + input").fill(serial_number)
    await create_unit_panel.get_by_role("button", name="Create Unit(s)").click()
    await expect(create_unit_panel.get_by_text(f"Created 1 unit(s): {serial_number}")).to_be_visible(timeout=10_000)

    orders = _unwrap(api.get(API_ORDERS, params={"limit": 200}))
    order = next((o for o in orders if o["order_number"] == order_number), None)
    assert order is not None, f"Order {order_number} not found after creation"
    assert order["status"] in {"released", "in_progress"}

    units = _unwrap(api.get(API_UNITS, params={"order_id": order["id"], "limit": 200}))
    unit = next((item for item in units if item["serial_number"] == serial_number), None)
    assert unit is not None, f"Unit {serial_number} not found after creation"
    return order, unit


def _cleanup_sqa_artifacts(api) -> None:
    orders = _unwrap(api.get(API_ORDERS, params={"limit": 200}))
    for order in orders:
        if not order["order_number"].startswith(SQA_ORDER_PREFIXES):
            continue

        units = _unwrap(api.get(API_UNITS, params={"order_id": order["id"], "limit": 200}))
        for unit in units:
            if not unit["serial_number"].startswith(SQA_UNIT_PREFIXES):
                continue
            if unit["status"] not in {"completed", "scrapped"}:
                resp = api.post(f"{API_UNITS}/{unit['id']}/scrap", json={"reason": "SQA cleanup"})
                if resp.status_code != 200:
                    refreshed = _unwrap(api.get(f"{API_UNITS}/{unit['id']}"))
                    assert refreshed["status"] == "scrapped", f"Could not scrap stale test unit {unit['serial_number']}: {resp.text}"

        lots = _unwrap(api.get(API_LOTS, params={"order_id": order["id"], "limit": 200}))
        for lot in lots:
            if not lot["lot_number"].startswith(SQA_LOT_PREFIXES):
                continue
            if lot["status"] not in {"completed", "scrapped"}:
                resp = api.post(f"{API_LOTS}/{lot['id']}/scrap", json={"reason": "SQA cleanup"})
                if resp.status_code != 200:
                    refreshed = _unwrap(api.get(f"{API_LOTS}/{lot['id']}"))
                    assert refreshed["status"] == "scrapped", f"Could not scrap stale test lot {lot['lot_number']}: {resp.text}"

        resp = api.delete(f"{API_ORDERS}/{order['id']}")
        assert resp.status_code == 204, f"Could not delete stale test order {order['order_number']}: {resp.text}"


async def _fill_step_parameters(page: Page, step_parameters: list[dict]) -> None:
    for param in step_parameters:
        row = page.locator("tr", has_text=param["name"]).first
        if param["data_type"] == "boolean":
            await row.locator("select").select_option("true")
        else:
            value = _pick_numeric_value(param) if param["data_type"] == "numeric" else f"SQA {param['name']}"
            await row.locator("input").fill(value)


async def _fill_data_collection(page: Page, data_definitions: list[dict]) -> None:
    for definition in data_definitions:
        label = definition["name"]
        if definition["data_type"] == "boolean":
            await page.locator(f"label:has-text('{label}') ~ select:visible").select_option("true")
        elif definition["data_type"] == "enum":
            select = page.locator(f"label:has-text('{label}') ~ select:visible")
            await select.select_option(index=1)
        else:
            await page.locator(f"label:has-text('{label}') ~ input:visible").fill(
                _pick_numeric_value(definition)
            )


async def _consume_bom_items(
    page: Page,
    api,
    step_id: str,
    materials_by_code: dict[str, dict],
) -> None:
    bom_resp = api.get(f"/process-segments/{step_id}/bom-items")
    bom_items = _unwrap(bom_resp)
    if not bom_items:
        return

    for item in bom_items:
        material = materials_by_code[item["material_code"]]
        lots_resp = api.get(API_MATERIAL_LOTS, params={"material_id": material["id"], "status": "available"})
        material_lots = _unwrap(lots_resp)
        matching = [lot for lot in material_lots if float(lot["quantity_on_hand"]) >= float(item["quantity"])]
        assert matching, f"No existing material lot can satisfy {item['material_code']}"
        chosen_lot = matching[0]

        row = page.locator("tr", has_text=item["material_code"]).first
        await row.locator("select").select_option(chosen_lot["id"])
        await row.locator("input").fill(str(item["quantity"]))
        await row.get_by_role("button", name="Consume").click()
        await expect(page.locator("div.bg-green-50", has_text=item["material_code"])).to_be_visible(timeout=10_000)


async def _process_current_step(
    page: Page,
    api,
    lot_id: str,
    expected_step_name: str,
    materials_by_code: dict[str, dict],
    *,
    result: str | None = None,
    disposition_contains: str | None = None,
) -> None:
    ctx = _unwrap(api.get(f"{API_LOTS}/{lot_id}/step-context"))
    assert ctx["wip"]["status"] == "queued"
    if ctx["step"] is not None:
        assert ctx["step"]["name"] == expected_step_name

    await page.get_by_label("Transition State").check()
    await page.get_by_role("button", name="Start").click()
    await expect(page.locator("div.bg-green-50", has_text="Started processing")).to_be_visible(timeout=15_000)

    ctx = _unwrap(api.get(f"{API_LOTS}/{lot_id}/step-context"))
    assert ctx["step"]["name"] == expected_step_name
    assert ctx["wip"]["status"] == "in_process"

    await _fill_data_collection(page, ctx["data_definitions"])
    await _fill_step_parameters(page, ctx["step_parameters"])
    await _consume_bom_items(page, api, ctx["step"]["id"], materials_by_code)

    if result is not None:
        result_select = page.locator("label:has-text('Result') ~ select:visible")
        if await result_select.count() > 0:
            await result_select.select_option(result)
    if disposition_contains is not None:
        disposition_select = page.locator("label:has-text('Disposition') ~ select:visible")
        if await disposition_select.count() > 0:
            options = disposition_select.locator("option")
            matched_value = None
            for index in range(await options.count()):
                option = options.nth(index)
                if disposition_contains in await option.inner_text():
                    matched_value = await option.get_attribute("value")
                    break
            assert matched_value is not None, f"No disposition option contains '{disposition_contains}'"
            await disposition_select.select_option(matched_value)

    qty_out = ctx["wip"].get("quantity")
    if qty_out is not None:
        qty_out_input = page.locator("label:has-text('Qty Out') ~ input:visible")
        if await qty_out_input.count() > 0:
            await qty_out_input.fill(str(int(qty_out)))
    qty_scrapped_input = page.locator("label:has-text('Qty Scrapped') ~ input:visible")
    if await qty_scrapped_input.count() > 0:
        await qty_scrapped_input.fill("0")

    await page.get_by_label("Transition State").check()
    await page.get_by_role("button", name="Complete").click()
    await expect(page.locator("div.bg-green-50", has_text="Step completed")).to_be_visible(timeout=15_000)


async def _process_current_unit_step(
    page: Page,
    api,
    unit_id: str,
    expected_step_name: str,
    materials_by_code: dict[str, dict],
    *,
    result: str | None = None,
    disposition_contains: str | None = None,
) -> None:
    ctx = _unwrap(api.get(f"{API_UNITS}/{unit_id}/step-context"))
    assert ctx["wip"]["status"] == "queued"
    if ctx["step"] is not None:
        assert ctx["step"]["name"] == expected_step_name

    await page.get_by_label("Transition State").check()
    await page.get_by_role("button", name="Start").click()
    await expect(page.locator("div.bg-green-50", has_text="Started processing")).to_be_visible(timeout=15_000)

    ctx = _unwrap(api.get(f"{API_UNITS}/{unit_id}/step-context"))
    assert ctx["step"]["name"] == expected_step_name
    assert ctx["wip"]["status"] == "in_process"

    await _fill_data_collection(page, ctx["data_definitions"])
    await _fill_step_parameters(page, ctx["step_parameters"])
    await _consume_bom_items(page, api, ctx["step"]["id"], materials_by_code)

    if result is not None:
        result_select = page.locator("label:has-text('Result') ~ select:visible")
        if await result_select.count() > 0:
            await result_select.select_option(result)
    if disposition_contains is not None:
        disposition_select = page.locator("label:has-text('Disposition') ~ select:visible")
        if await disposition_select.count() > 0:
            options = disposition_select.locator("option")
            matched_value = None
            for index in range(await options.count()):
                option = options.nth(index)
                if disposition_contains in await option.inner_text():
                    matched_value = await option.get_attribute("value")
                    break
            assert matched_value is not None, f"No disposition option contains '{disposition_contains}'"
            await disposition_select.select_option(matched_value)

    await page.get_by_label("Transition State").check()
    await page.get_by_role("button", name="Complete").click()
    await expect(page.locator("div.bg-green-50", has_text="Step completed")).to_be_visible(timeout=15_000)


def _load_product_setup(api, product_code: str) -> tuple[dict, dict[str, dict]]:
    products_resp = api.get(API_PRODUCTS, params={"limit": 200})
    products = _unwrap(products_resp)
    product = next((p for p in products if p["code"] == product_code), None)
    assert product is not None, f"{product_code} product not found -- seed the demo data first"

    materials_resp = api.get(API_MATERIALS, params={"limit": 200})
    materials = _unwrap(materials_resp)
    materials_by_code = {material["code"]: material for material in materials}
    return product, materials_by_code


@pytest.mark.ui
async def test_rt_wip_lot_normal_path(page: Page, api, mes_urls) -> None:
    _cleanup_sqa_artifacts(api)
    product, materials_by_code = _load_product_setup(api, "FG-OJ-1L")

    token = _stamp()
    order_number = f"SQA-WIP-{token}"
    lot_number = f"SQA-OJ-{token}"
    rt_url = mes_urls["rt"]

    _, lot = await _create_order_and_lot(page, api, rt_url, product["id"], order_number, lot_number)

    await _open_active_lot(page, lot_number)

    await _process_current_step(page, api, lot["id"], "Blending", materials_by_code)
    await _process_current_step(page, api, lot["id"], "Pasteurization", materials_by_code)
    await _process_current_step(
        page,
        api,
        lot["id"],
        "Quality Testing",
        materials_by_code,
        result="pass",
        disposition_contains="QC Pass",
    )
    await _process_current_step(page, api, lot["id"], "Filling & Capping", materials_by_code)
    await _process_current_step(page, api, lot["id"], "Labeling & Packing", materials_by_code)

    final_lot = _unwrap(api.get(f"{API_LOTS}/{lot['id']}"))
    assert final_lot["status"] == "completed"

    final_ctx = _unwrap(api.get(f"{API_LOTS}/{lot['id']}/step-context"))
    route_steps = {step["id"]: step["name"] for step in final_ctx["route_steps"]}
    history = _unwrap(api.get(f"{API_LOTS}/{lot['id']}/history"))
    assert all(float(record["quantity_scrapped"]) == 0 for record in history)
    step_names = [route_steps[record["step_id"]] for record in history]
    assert step_names == [
        "Blending",
        "Pasteurization",
        "Quality Testing",
        "Filling & Capping",
        "Labeling & Packing",
    ]
    await expect(page.get_by_text("✅ All steps completed")).to_be_visible(timeout=10_000)


@pytest.mark.ui
async def test_rt_wip_lot_mrb_rework_loop(page: Page, api, mes_urls) -> None:
    _cleanup_sqa_artifacts(api)
    product, materials_by_code = _load_product_setup(api, "FG-OJ-1L")

    token = _stamp()
    order_number = f"SQA-MRB-{token}"
    lot_number = f"SQA-MRB-OJ-{token}"
    rt_url = mes_urls["rt"]

    _, lot = await _create_order_and_lot(page, api, rt_url, product["id"], order_number, lot_number)

    await _open_active_lot(page, lot_number)

    await _process_current_step(page, api, lot["id"], "Blending", materials_by_code)
    await _process_current_step(page, api, lot["id"], "Pasteurization", materials_by_code)
    await _process_current_step(
        page,
        api,
        lot["id"],
        "Quality Testing",
        materials_by_code,
        result="fail",
        disposition_contains="Escalate to MRB",
    )

    ctx = _unwrap(api.get(f"{API_LOTS}/{lot['id']}/step-context"))
    assert ctx["step"]["name"] == "MRB Review"
    assert ctx["wip"]["status"] == "queued"

    await _process_current_step(
        page,
        api,
        lot["id"],
        "MRB Review",
        materials_by_code,
        disposition_contains="Return to Blend",
    )

    ctx = _unwrap(api.get(f"{API_LOTS}/{lot['id']}/step-context"))
    assert ctx["step"]["name"] in {"Re‑Blend (Rework)", "Re-Blend (Rework)"}
    assert ctx["wip"]["status"] == "queued"

    await _process_current_step(
        page,
        api,
        lot["id"],
        ctx["step"]["name"],
        materials_by_code,
        disposition_contains="Rework Complete",
    )
    await _process_current_step(page, api, lot["id"], "Pasteurization", materials_by_code)

    final_lot = _unwrap(api.get(f"{API_LOTS}/{lot['id']}"))
    assert final_lot["status"] == "queued"
    assert final_lot["current_step_name"] == "Quality Testing"

    final_ctx = _unwrap(api.get(f"{API_LOTS}/{lot['id']}/step-context"))
    assert final_ctx["step"]["name"] == "Quality Testing"
    assert final_ctx["wip"]["status"] == "queued"
    route_steps = {step["id"]: step["name"] for step in final_ctx["route_steps"]}
    history = _unwrap(api.get(f"{API_LOTS}/{lot['id']}/history"))
    step_names = [route_steps[record["step_id"]] for record in history]
    assert step_names == [
        "Blending",
        "Pasteurization",
        "Quality Testing",
        "MRB Review",
        ctx["step"]["name"],
        "Pasteurization",
    ]


@pytest.mark.ui
async def test_rt_wip_unit_electronics_normal_path(page: Page, api, mes_urls) -> None:
    _cleanup_sqa_artifacts(api)
    product, materials_by_code = _load_product_setup(api, "FG-ECB-100")

    token = _stamp()
    order_number = f"SQA-ECB-{token}"
    serial_number = f"SQA-ECB-SN-{token}"
    rt_url = mes_urls["rt"]

    _, unit = await _create_order_and_unit(page, api, rt_url, product["id"], order_number, serial_number)

    await _open_active_unit(page, serial_number)

    await _process_current_unit_step(page, api, unit["id"], "Solder Paste Application", materials_by_code)
    await _process_current_unit_step(page, api, unit["id"], "SMD Placement", materials_by_code)
    await _process_current_unit_step(page, api, unit["id"], "Reflow Soldering", materials_by_code)
    await _process_current_unit_step(
        page,
        api,
        unit["id"],
        "Automated Optical Inspection",
        materials_by_code,
        result="pass",
        disposition_contains="AOI Pass",
    )
    await _process_current_unit_step(page, api, unit["id"], "Through-Hole & Conformal Coat", materials_by_code)
    await _process_current_unit_step(
        page,
        api,
        unit["id"],
        "Functional Test",
        materials_by_code,
        result="pass",
        disposition_contains="Functional Test Pass",
    )
    await _process_current_unit_step(page, api, unit["id"], "Final Packaging & Labeling", materials_by_code)

    final_unit = _unwrap(api.get(f"{API_UNITS}/{unit['id']}"))
    assert final_unit["status"] == "completed"

    final_ctx = _unwrap(api.get(f"{API_UNITS}/{unit['id']}/step-context"))
    route_steps = {step["id"]: step["name"] for step in final_ctx["route_steps"]}
    history = _unwrap(api.get(f"{API_UNITS}/{unit['id']}/history"))
    step_names = [route_steps[record["step_id"]] for record in history]
    assert step_names == [
        "Solder Paste Application",
        "SMD Placement",
        "Reflow Soldering",
        "Automated Optical Inspection",
        "Through-Hole & Conformal Coat",
        "Functional Test",
        "Final Packaging & Labeling",
    ]
    await expect(page.get_by_text("✅ All steps completed")).to_be_visible(timeout=10_000)