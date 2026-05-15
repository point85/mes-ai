# Defect Log

> Running log of defects discovered by SQA tests and later confirmed fixed.

Entries are appended automatically by the shared pytest harness in SQA/conftest.py.

## [OPEN] 2026-05-14T01:33:00Z - modules/SQA-DT/test_route_editor_crud.py::test_route_step_crud
- Summary: E   Error: element(s) not found
- First seen: 2026-05-14T01:33:00Z
- Last seen: 2026-05-14T01:33:00Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:148: in test_route_step_crud
    await _select_route(page, route_name=route["name"], route_version=route["version"])
SQA\modules\SQA-DT\test_route_editor_crud.py:86: in _select_route
    await expect(page.get_by_role("heading", name=f"Steps — {route_name}")).to_be_visible(timeout=8_000)
E   AssertionError: Locator expected to be visible
E   Actual value: None
E   Error: element(s) not found
E   Call log:
E     - Expect "to_be_visible" with timeout 8000ms
E     - waiting for get_by_role("heading", name="Steps — SQA Step Route")
```

## [OPEN] 2026-05-14T01:33:12Z - modules/SQA-DT/test_route_editor_crud.py::test_route_product_assignment
- Summary: E   Error: element(s) not found
- First seen: 2026-05-14T01:33:12Z
- Last seen: 2026-05-14T01:33:12Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:215: in test_route_product_assignment
    await _select_route(page, route_name=route["name"], route_version=route["version"])
SQA\modules\SQA-DT\test_route_editor_crud.py:86: in _select_route
    await expect(page.get_by_role("heading", name=f"Steps — {route_name}")).to_be_visible(timeout=8_000)
E   AssertionError: Locator expected to be visible
E   Actual value: None
E   Error: element(s) not found
E   Call log:
E     - Expect "to_be_visible" with timeout 8000ms
E     - waiting for get_by_role("heading", name="Steps — SQA Product Assignment Route")
```

## [RESOLVED] 2026-05-14T01:33:47Z - modules/SQA-DT/test_route_editor_crud.py::test_route_step_crud
- Summary: E   Error: element(s) not found
- First seen: 2026-05-14T01:33:00Z
- Last seen failing run: 2026-05-14T01:33:00Z
- Occurrences before fix: 1
- Status: resolved
- Resolved at: 2026-05-14T01:33:47Z

## [OPEN] 2026-05-14T01:33:48Z - modules/SQA-DT/test_route_editor_crud.py::test_route_product_assignment
- Summary: E   AssertionError: Product setup failed: {"error":{"code":"DUPLICATE_PRODUCT","message":"Product with code 'SQA_PROD_ROUTE_ASSIGN' version '1.0' already exists","details":{"code":"SQA_PROD_ROUTE_ASSIGN","version":"1.0"}},"meta":{"timestamp":"2026-05-14T01:33:48.268722+00:00"}}
- First seen: 2026-05-14T01:33:48Z
- Last seen: 2026-05-14T01:33:48Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:212: in test_route_product_assignment
    product = _create_product(api, uom_id=uom["id"])
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
SQA\modules\SQA-DT\test_route_editor_crud.py:69: in _create_product
    assert resp.status_code in (200, 201), f"Product setup failed: {resp.text}"
E   AssertionError: Product setup failed: {"error":{"code":"DUPLICATE_PRODUCT","message":"Product with code 'SQA_PROD_ROUTE_ASSIGN' version '1.0' already exists","details":{"code":"SQA_PROD_ROUTE_ASSIGN","version":"1.0"}},"meta":{"timestamp":"2026-05-14T01:33:48.268722+00:00"}}
E   assert 409 in (200, 201)
E    +  where 409 = <Response [409 Conflict]>.status_code
```

## [OPEN] 2026-05-14T01:34:17Z - modules/SQA-DT/test_route_editor_crud.py::test_route_product_assignment
- Summary: E   playwright._impl._errors.Error: Locator.click: Error: strict mode violation: get_by_role("button", name="Assign") resolved to 2 elements:
- First seen: 2026-05-14T01:34:17Z
- Last seen: 2026-05-14T01:34:17Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:218: in test_route_product_assignment
    await page.get_by_role("button", name="Assign").click()
.venv\Lib\site-packages\playwright\async_api\_generated.py:16212: in click
    await self._impl_obj.click(
.venv\Lib\site-packages\playwright\_impl\_locator.py:162: in click
    return await self._frame._click(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv\Lib\site-packages\playwright\_impl\_frame.py:566: in _click
    await self._channel.send("click", self._timeout, locals_to_params(locals()))
.venv\Lib\site-packages\playwright\_impl\_connection.py:69: in send
    return await self._connection.wrap_api_call(
.venv\Lib\site-packages\playwright\_impl\_connection.py:559: in wrap_api_call
    raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E   playwright._impl._errors.Error: Locator.click: Error: strict mode violation: get_by_role("button", name="Assign") resolved to 2 elements:
E       1) <button class="flex-1 text-left px-4 py-3 min-w-0">…</button> aka get_by_role("button", name="SQA Product Assignment Route")
E       2) <button class="inline-flex items-center gap-1 rounded-md bg-indigo-600 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 transition-colors">…</button> aka get_by_role("button", name="Assign", exact=True)
E
E   Call log:
E     - waiting for get_by_role("button", name="Assign")
```

## [OPEN] 2026-05-14T01:34:50Z - modules/SQA-DT/test_route_editor_crud.py::test_route_product_assignment
- Summary: E    +  where False = any(<generator object test_route_product_assignment.<locals>.<genexpr> at 0x00000217C9F93BC0>)
- First seen: 2026-05-14T01:34:50Z
- Last seen: 2026-05-14T01:34:50Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:231: in test_route_product_assignment
    assert any(item["product_id"] == product["id"] for item in assignments)
E   assert False
E    +  where False = any(<generator object test_route_product_assignment.<locals>.<genexpr> at 0x00000217C9F93BC0>)
```

## [OPEN] 2026-05-14T01:35:53Z - modules/SQA-DT/test_route_editor_crud.py::test_route_product_assignment
- Summary: E   playwright._impl._errors.Error: Locator.click: Error: strict mode violation: get_by_text("Products", exact=True) resolved to 3 elements:
- First seen: 2026-05-14T01:35:53Z
- Last seen: 2026-05-14T01:35:53Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:219: in test_route_product_assignment
    await page.get_by_text("Products", exact=True).click()
.venv\Lib\site-packages\playwright\async_api\_generated.py:16212: in click
    await self._impl_obj.click(
.venv\Lib\site-packages\playwright\_impl\_locator.py:162: in click
    return await self._frame._click(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv\Lib\site-packages\playwright\_impl\_frame.py:566: in _click
    await self._channel.send("click", self._timeout, locals_to_params(locals()))
.venv\Lib\site-packages\playwright\_impl\_connection.py:69: in send
    return await self._connection.wrap_api_call(
.venv\Lib\site-packages\playwright\_impl\_connection.py:559: in wrap_api_call
    raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E   playwright._impl._errors.Error: Locator.click: Error: strict mode violation: get_by_text("Products", exact=True) resolved to 3 elements:
E       1) <span class="block px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Products</span> aka locator("span").filter(has_text="Products")
E       2) <a href="/products" data-discover="true" class="flex flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium transition-colors text-gray-700 hover:bg-gray-100">…</a> aka get_by_role("link", name="Products")
E       3) <label class="inline-flex items-center gap-1.5 text-xs font-medium text-gray-700 cursor-pointer">…</label> aka get_by_role("main").get_by_text("Products", exact=True)
E
E   Call log:
E     - waiting for get_by_text("Products", exact=True)
```

## [RESOLVED] 2026-05-14T01:36:22Z - modules/SQA-DT/test_route_editor_crud.py::test_route_product_assignment
- Summary: E   playwright._impl._errors.Error: Locator.click: Error: strict mode violation: get_by_text("Products", exact=True) resolved to 3 elements:
- First seen: 2026-05-14T01:35:53Z
- Last seen failing run: 2026-05-14T01:35:53Z
- Occurrences before fix: 1
- Status: resolved
- Resolved at: 2026-05-14T01:36:22Z

## [OPEN] 2026-05-14T03:06:53Z - modules/SQA-DT/test_route_editor_crud.py::test_route_disposition_editor_crud
- Summary: E   playwright._impl._errors.TimeoutError: Locator.fill: Timeout 30000ms exceeded.
- First seen: 2026-05-14T03:06:53Z
- Last seen: 2026-05-14T03:06:53Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:265: in test_route_disposition_editor_crud
    await page.get_by_label("Code").fill(disposition_code)
.venv\Lib\site-packages\playwright\async_api\_generated.py:16552: in fill
    await self._impl_obj.fill(
.venv\Lib\site-packages\playwright\_impl\_locator.py:215: in fill
    return await self._frame.fill(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv\Lib\site-packages\playwright\_impl\_frame.py:607: in fill
    await self._fill(**locals_to_params(locals()))
.venv\Lib\site-packages\playwright\_impl\_frame.py:619: in _fill
    await self._channel.send("fill", self._timeout, locals_to_params(locals()))
.venv\Lib\site-packages\playwright\_impl\_connection.py:69: in send
    return await self._connection.wrap_api_call(
.venv\Lib\site-packages\playwright\_impl\_connection.py:559: in wrap_api_call
    raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E   playwright._impl._errors.TimeoutError: Locator.fill: Timeout 30000ms exceeded.
E   Call log:
E     - waiting for get_by_label("Code")
```

## [OPEN] 2026-05-14T03:07:16Z - modules/SQA-DT/test_route_editor_crud.py::test_route_disposition_editor_crud
- Summary: E   Error: strict mode violation: locator("tr").filter(has_text="SQA_ROUTE_DISP_8fb9fa5e").locator("td").filter(has_text="SQA Route Disposition") resolved to 2 elements:
- First seen: 2026-05-14T03:07:16Z
- Last seen: 2026-05-14T03:07:16Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:273: in test_route_disposition_editor_crud
    await expect(disposition_row.locator("td", has_text="SQA Route Disposition")).to_be_visible()
E   AssertionError: Locator expected to be visible
E   Actual value: None
E   Error: strict mode violation: locator("tr").filter(has_text="SQA_ROUTE_DISP_8fb9fa5e").locator("td").filter(has_text="SQA Route Disposition") resolved to 2 elements:
E       1) <td class="py-2 px-2 text-sm text-gray-900">SQA Route Disposition</td> aka get_by_role("cell", name="SQA Route Disposition", exact=True)
E       2) <td class="py-2 px-2 text-sm text-gray-500">SQA route disposition create path</td> aka get_by_role("cell", name="SQA route disposition create")
E
E   Call log:
E     - Expect "to_be_visible" with timeout 5000ms
E     - waiting for locator("tr").filter(has_text="SQA_ROUTE_DISP_8fb9fa5e").locator("td").filter(has_text="SQA Route Disposition")
```

## [RESOLVED] 2026-05-14T03:07:40Z - modules/SQA-DT/test_route_editor_crud.py::test_route_disposition_editor_crud
- Summary: E   Error: strict mode violation: locator("tr").filter(has_text="SQA_ROUTE_DISP_8fb9fa5e").locator("td").filter(has_text="SQA Route Disposition") resolved to 2 elements:
- First seen: 2026-05-14T03:07:16Z
- Last seen failing run: 2026-05-14T03:07:16Z
- Occurrences before fix: 1
- Status: resolved
- Resolved at: 2026-05-14T03:07:40Z

## [OPEN] 2026-05-14T03:15:54Z - modules/SQA-DT/test_route_editor_crud.py::test_route_step_disposition_wiring
- Summary: E   AssertionError: assert ['SQA_ROUTE_DISP_IN_ef415f'] == ['SQA_ROUTE_DISP_IN_4fdf7e']
- First seen: 2026-05-14T03:15:54Z
- Last seen: 2026-05-14T03:15:54Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:356: in test_route_step_disposition_wiring
    assert [item["code"] for item in updated_detail["input_dispositions"]] == [input_b["code"]]
E   AssertionError: assert ['SQA_ROUTE_DISP_IN_ef415f'] == ['SQA_ROUTE_DISP_IN_4fdf7e']
E
E     At index 0 diff: [0m[33m'[39;49;00m[33mSQA_ROUTE_DISP_IN_ef415f[39;49;00m[33m'[39;49;00m[90m[39;49;00m != [0m[33m'[39;49;00m[33mSQA_ROUTE_DISP_IN_4fdf7e[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E
E     Full diff:
E     [0m[90m [39;49;00m [[90m[39;49;00m
E     [91m-     'SQA_ROUTE_DISP_IN_4fdf7e',[39;49;00m[90m[39;49;00m
E     ?                          ----[90m[39;49;00m...
E
E     ...Full output truncated (3 lines hidden), use '-vv' to show
```

## [OPEN] 2026-05-14T03:17:05Z - modules/SQA-DT/test_route_editor_crud.py::test_route_step_disposition_wiring
- Summary: E   AssertionError: assert ['SQA_ROUTE_DISP_IN_cce13b'] == ['SQA_ROUTE_DISP_IN_ce43b0']
- First seen: 2026-05-14T03:17:05Z
- Last seen: 2026-05-14T03:17:05Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:363: in test_route_step_disposition_wiring
    assert [item["code"] for item in updated_detail["input_dispositions"]] == [input_b["code"]]
E   AssertionError: assert ['SQA_ROUTE_DISP_IN_cce13b'] == ['SQA_ROUTE_DISP_IN_ce43b0']
E
E     At index 0 diff: [0m[33m'[39;49;00m[33mSQA_ROUTE_DISP_IN_cce13b[39;49;00m[33m'[39;49;00m[90m[39;49;00m != [0m[33m'[39;49;00m[33mSQA_ROUTE_DISP_IN_ce43b0[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E
E     Full diff:
E     [0m[90m [39;49;00m [[90m[39;49;00m
E     [91m-     'SQA_ROUTE_DISP_IN_ce43b0',[39;49;00m[90m[39;49;00m
E     ?                          ^  -[90m[39;49;00m...
E
E     ...Full output truncated (3 lines hidden), use '-vv' to show
```

## [OPEN] 2026-05-14T03:18:11Z - modules/SQA-DT/test_route_editor_crud.py::test_route_step_disposition_wiring
- Summary: E   Error: element(s) not found
- First seen: 2026-05-14T03:18:11Z
- Last seen: 2026-05-14T03:18:11Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:307: in test_route_step_disposition_wiring
    await _open_routes_page(page)
SQA\modules\SQA-DT\test_route_editor_crud.py:35: in _open_routes_page
    await expect(page.get_by_role("heading", name="Route Editor")).to_be_visible(timeout=10_000)
E   AssertionError: Locator expected to be visible
E   Actual value: None
E   Error: element(s) not found
E   Call log:
E     - Expect "to_be_visible" with timeout 10000ms
E     - waiting for get_by_role("heading", name="Route Editor")
```

## [OPEN] 2026-05-14T03:18:43Z - modules/SQA-DT/test_route_editor_crud.py::test_route_step_disposition_wiring
- Summary: E   AssertionError: assert ['SQA_ROUTE_DISP_IN_7acda6'] == ['SQA_ROUTE_DISP_IN_8308a3']
- First seen: 2026-05-14T03:18:43Z
- Last seen: 2026-05-14T03:18:43Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:365: in test_route_step_disposition_wiring
    assert [item["code"] for item in updated_detail["input_dispositions"]] == [input_b["code"]]
E   AssertionError: assert ['SQA_ROUTE_DISP_IN_7acda6'] == ['SQA_ROUTE_DISP_IN_8308a3']
E
E     At index 0 diff: [0m[33m'[39;49;00m[33mSQA_ROUTE_DISP_IN_7acda6[39;49;00m[33m'[39;49;00m[90m[39;49;00m != [0m[33m'[39;49;00m[33mSQA_ROUTE_DISP_IN_8308a3[39;49;00m[33m'[39;49;00m[90m[39;49;00m
E
E     Full diff:
E     [0m[90m [39;49;00m [[90m[39;49;00m
E     [91m-     'SQA_ROUTE_DISP_IN_8308a3',[39;49;00m[90m[39;49;00m
E     ?                        ^^^^ ^[90m[39;49;00m...
E
E     ...Full output truncated (3 lines hidden), use '-vv' to show
```

## [RESOLVED] 2026-05-14T03:20:59Z - modules/SQA-DT/test_route_editor_crud.py::test_route_step_disposition_wiring
- Summary: E   AssertionError: assert ['SQA_ROUTE_DISP_IN_7acda6'] == ['SQA_ROUTE_DISP_IN_8308a3']
- First seen: 2026-05-14T03:18:43Z
- Last seen failing run: 2026-05-14T03:18:43Z
- Occurrences before fix: 1
- Status: resolved
- Resolved at: 2026-05-14T03:20:59Z

## [OPEN] 2026-05-14T15:28:46Z - modules/SQA-DT/test_reason_crud.py::test_reason_edit
- Summary: E   Error: strict mode violation: locator("tr").filter(has_text="0108").locator("td").filter(has_text="SQA Edited Reason") resolved to 2 elements:
- First seen: 2026-05-14T15:28:46Z
- Last seen: 2026-05-14T15:28:46Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_reason_crud.py:140: in test_reason_edit
    await expect(updated_row.locator("td", has_text="SQA Edited Reason")).to_be_visible()
E   AssertionError: Locator expected to be visible
E   Actual value: None
E   Error: strict mode violation: locator("tr").filter(has_text="0108").locator("td").filter(has_text="SQA Edited Reason") resolved to 2 elements:
E       1) <td class="py-2 px-2 text-sm text-gray-900">SQA Edited Reason</td> aka get_by_role("cell", name="SQA Edited Reason", exact=True)
E       2) <td class="py-2 px-2 text-sm text-gray-500">SQA edited reason</td> aka get_by_role("cell", name="SQA edited reason", exact=True)
E
E   Call log:
E     - Expect "to_be_visible" with timeout 5000ms
E     - waiting for locator("tr").filter(has_text="0108").locator("td").filter(has_text="SQA Edited Reason")
```

## [OPEN] 2026-05-14T15:28:49Z - modules/SQA-DT/test_reason_crud.py::test_reason_add_child
- Summary: E   Error: strict mode violation: locator("tr").filter(has_text="CA74").locator("td").filter(has_text="SQA Child Reason") resolved to 2 elements:
- First seen: 2026-05-14T15:28:49Z
- Last seen: 2026-05-14T15:28:49Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_reason_crud.py:206: in test_reason_add_child
    await expect(child_row.locator("td", has_text="SQA Child Reason")).to_be_visible()
E   AssertionError: Locator expected to be visible
E   Actual value: None
E   Error: strict mode violation: locator("tr").filter(has_text="CA74").locator("td").filter(has_text="SQA Child Reason") resolved to 2 elements:
E       1) <td class="py-2 px-2 text-sm text-gray-900">SQA Child Reason</td> aka get_by_role("cell", name="SQA Child Reason", exact=True)
E       2) <td class="py-2 px-2 text-sm text-gray-500">SQA child reason</td> aka get_by_role("cell", name="SQA child reason", exact=True)
E
E   Call log:
E     - Expect "to_be_visible" with timeout 5000ms
E     - waiting for locator("tr").filter(has_text="CA74").locator("td").filter(has_text="SQA Child Reason")
```

## [RESOLVED] 2026-05-14T15:29:26Z - modules/SQA-DT/test_reason_crud.py::test_reason_edit
- Summary: E   Error: strict mode violation: locator("tr").filter(has_text="0108").locator("td").filter(has_text="SQA Edited Reason") resolved to 2 elements:
- First seen: 2026-05-14T15:28:46Z
- Last seen failing run: 2026-05-14T15:28:46Z
- Occurrences before fix: 1
- Status: resolved
- Resolved at: 2026-05-14T15:29:26Z

## [RESOLVED] 2026-05-14T15:29:29Z - modules/SQA-DT/test_reason_crud.py::test_reason_add_child
- Summary: E   Error: strict mode violation: locator("tr").filter(has_text="CA74").locator("td").filter(has_text="SQA Child Reason") resolved to 2 elements:
- First seen: 2026-05-14T15:28:49Z
- Last seen failing run: 2026-05-14T15:28:49Z
- Occurrences before fix: 1
- Status: resolved
- Resolved at: 2026-05-14T15:29:29Z

## [OPEN] 2026-05-14T15:33:15Z - modules/SQA-DT/test_auth_admin_crud.py::test_user_edit
- Summary: E   AssertionError: {"error":{"code":"RESOURCE_NOT_FOUND","message":"User with id '63ec20fe-3ac0-4656-b5a2-70c0feb3899c' not found","details":null},"meta":{"timestamp":"2026-05-14T15:33:15.410719+00:00"}}
- First seen: 2026-05-14T15:33:15Z
- Last seen: 2026-05-14T15:33:15Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_auth_admin_crud.py:244: in test_user_edit
    assert resp.status_code == 200, resp.text
E   AssertionError: {"error":{"code":"RESOURCE_NOT_FOUND","message":"User with id '63ec20fe-3ac0-4656-b5a2-70c0feb3899c' not found","details":null},"meta":{"timestamp":"2026-05-14T15:33:15.410719+00:00"}}
E   assert 404 == 200
E    +  where 404 = <Response [404 Not Found]>.status_code
```

## [RESOLVED] 2026-05-14T15:34:01Z - modules/SQA-DT/test_auth_admin_crud.py::test_user_edit
- Summary: E   AssertionError: {"error":{"code":"RESOURCE_NOT_FOUND","message":"User with id '63ec20fe-3ac0-4656-b5a2-70c0feb3899c' not found","details":null},"meta":{"timestamp":"2026-05-14T15:33:15.410719+00:00"}}
- First seen: 2026-05-14T15:33:15Z
- Last seen failing run: 2026-05-14T15:33:15Z
- Occurrences before fix: 1
- Status: resolved
- Resolved at: 2026-05-14T15:34:01Z

## [OPEN] 2026-05-14T15:45:13Z - modules/SQA-DT/test_route_editor_crud.py::test_route_step_equipment_requirements_editor
- Summary: E   AssertionError: assert 'required' == 'preferred'
- First seen: 2026-05-14T15:45:13Z
- Last seen: 2026-05-14T15:45:13Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:654: in test_route_step_equipment_requirements_editor
    assert created["use_type"] == "preferred"
E   AssertionError: assert 'required' == 'preferred'
E
E     [0m[91m- preferred[39;49;00m[90m[39;49;00m
E     [92m+ required[39;49;00m[90m[39;49;00m
```

## [OPEN] 2026-05-14T15:45:24Z - modules/SQA-DT/test_route_editor_crud.py::test_route_step_material_requirements_editor
- Summary: E   Error: element(s) not found
- First seen: 2026-05-14T15:45:24Z
- Last seen: 2026-05-14T15:45:24Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:685: in test_route_step_material_requirements_editor
    await expect(requirement_row).to_be_visible(timeout=8_000)
E   AssertionError: Locator expected to be visible
E   Actual value: None
E   Error: element(s) not found
E   Call log:
E     - Expect "to_be_visible" with timeout 8000ms
E     - waiting for get_by_role("dialog").locator("xpath=.//h4[normalize-space()='Material Requirements']/ancestor::div[contains(@class,'rounded-md')][1]").locator("li").filter(has_text="SQA_MAT_e2adae8c")
```

## [RESOLVED] 2026-05-14T15:55:10Z - modules/SQA-DT/test_route_editor_crud.py::test_route_step_equipment_requirements_editor
- Summary: E   AssertionError: assert 'required' == 'preferred'
- First seen: 2026-05-14T15:45:13Z
- Last seen failing run: 2026-05-14T15:53:39Z
- Occurrences before fix: 3
- Status: resolved
- Resolved at: 2026-05-14T15:55:10Z

## [OPEN] 2026-05-14T17:28:06Z - modules/SQA-DT/test_route_editor_crud.py::test_route_step_material_requirements_editor
- Summary: E   AssertionError: Locator expected to have Value ''
- First seen: 2026-05-14T17:28:06Z
- Last seen: 2026-05-14T17:28:06Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-DT\test_route_editor_crud.py:703: in test_route_step_material_requirements_editor
    await expect(section.locator("select").nth(0)).to_have_value("", timeout=8_000)
E   AssertionError: Locator expected to have Value ''
E   Actual value: 75084474-88fb-4c34-917c-bedaf0bca5e3
E   Call log:
E     - Expect "to_have_value" with timeout 8000ms
E     - waiting for get_by_role("dialog").locator("xpath=.//h4[normalize-space()='Material Requirements']/ancestor::div[contains(@class,'rounded-md')][1]").locator("select").first
E       11 × locator resolved to <select class="rounded border border-gray-300 bg-white px-2 py-1 text-xs">…</select>
E          - unexpected value "75084474-88fb-4c34-917c-bedaf0bca5e3"
```

## [RESOLVED] 2026-05-14T17:31:33Z - modules/SQA-DT/test_route_editor_crud.py::test_route_step_material_requirements_editor
- Summary: E   AssertionError: Locator expected to have Value ''
- First seen: 2026-05-14T17:28:06Z
- Last seen failing run: 2026-05-14T17:28:06Z
- Occurrences before fix: 1
- Status: resolved
- Resolved at: 2026-05-14T17:31:33Z

## [OPEN] 2026-05-15T00:29:11Z - modules/SQA-RT/test_inventory_operations.py::test_rt_inventory_operations
- Summary: ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- First seen: 2026-05-15T00:29:11Z
- Last seen: 2026-05-15T00:29:11Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
page = <Page url='about:blank'>
api = <httpx.Client object at 0x000001C535AB5940>
mes_urls = {'api': 'http://localhost:8081/api/v1', 'dt': 'http://localhost:5177', 'rt': 'http://localhost:5176', 'server': 'http://localhost:8081'}

    @pytest.mark.ui
    @pytest.mark.usefixtures("uom_cleanup", "material_cleanup", "storage_location_cleanup")
    async def test_rt_inventory_operations(page: Page, api, mes_urls) -> None:
        # 1. API Seeds
        uom = _create_scalar_uom(api, symbol=_unique_code("SQA_UOM"), name="SQA Material UoM")
        mat = _create_material(api, uom_id=uom["id"], code=_unique_code("SQA_MAT"), name="SQA Inventory Material")
        loc1 = _create_storage_location(api, code=_unique_code("WH1"), name="Warehouse 1")
        loc2 = _create_storage_location(api, code=_unique_code("WH2"), name="Warehouse 2")

        rt_url = mes_urls.get("rt", "http://localhost:5176")

        # 2. Go to RT Inventory Page
>       await page.goto(rt_url)

SQA\modules\SQA-RT\test_inventory_operations.py:97:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
.venv\Lib\site-packages\playwright\async_api\_generated.py:9365: in goto
    await self._impl_obj.goto(
.venv\Lib\site-packages\playwright\_impl\_page.py:552: in goto
    return await self._main_frame.goto(**locals_to_params(locals()))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

## [OPEN] 2026-05-15T00:29:46Z - modules/SQA-RT/test_inventory_operations.py::test_rt_inventory_operations
- Summary: E       Error: strict mode violation: get_by_role("heading", name="Inventory") resolved to 2 elements:
- First seen: 2026-05-15T00:29:46Z
- Last seen: 2026-05-15T00:29:46Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
page = <Page url='http://localhost:5176/'>
api = <httpx.Client object at 0x000001CB8EE75940>
mes_urls = {'api': 'http://localhost:8081/api/v1', 'dt': 'http://localhost:5177', 'rt': 'http://localhost:5176', 'server': 'http://localhost:8081'}

    @pytest.mark.ui
    @pytest.mark.usefixtures("uom_cleanup", "material_cleanup", "storage_location_cleanup")
    async def test_rt_inventory_operations(page: Page, api, mes_urls) -> None:
        # 1. API Seeds
        uom = _create_scalar_uom(api, symbol=_unique_code("SQA_UOM"), name="SQA Material UoM")
        mat = _create_material(api, uom_id=uom["id"], code=_unique_code("SQA_MAT"), name="SQA Inventory Material")
        loc1 = _create_storage_location(api, code=_unique_code("WH1"), name="Warehouse 1")
        loc2 = _create_storage_location(api, code=_unique_code("WH2"), name="Warehouse 2")

        rt_url = mes_urls.get("rt", "http://localhost:5176")

        # 2. Go to RT Inventory Page
        await page.goto(rt_url)
        await page.get_by_role("button", name="Inventory").click()
>       await expect(page.get_by_role("heading", name="Inventory")).to_be_visible(timeout=10000)
E       AssertionError: Locator expected to be visible
E       Actual value: None
E       Error: strict mode violation: get_by_role("heading", name="Inventory") resolved to 2 elements:
E           1) <h2 class="text-2xl font-bold text-gray-800">Inventory</h2> aka get_by_role("heading", name="Inventory", exact=True)
E           2) <h3 class="text-lg font-semibold text-gray-700 capitalize">receive Inventory</h3> aka get_by_role("heading", name="receive Inventory")
E
```

## [OPEN] 2026-05-15T00:30:37Z - modules/SQA-RT/test_inventory_operations.py::test_rt_inventory_operations
- Summary: # Dialog for new lot
- First seen: 2026-05-15T00:30:37Z
- Last seen: 2026-05-15T00:30:37Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
page = <Page url='http://localhost:5176/'>
api = <httpx.Client object at 0x0000022FD5655940>
mes_urls = {'api': 'http://localhost:8081/api/v1', 'dt': 'http://localhost:5177', 'rt': 'http://localhost:5176', 'server': 'http://localhost:8081'}

    @pytest.mark.ui
    @pytest.mark.usefixtures("uom_cleanup", "material_cleanup", "storage_location_cleanup")
    async def test_rt_inventory_operations(page: Page, api, mes_urls) -> None:
        # 1. API Seeds
        uom = _create_scalar_uom(api, symbol=_unique_code("SQA_UOM"), name="SQA Material UoM")
        mat = _create_material(api, uom_id=uom["id"], code=_unique_code("SQA_MAT"), name="SQA Inventory Material")
        loc1 = _create_storage_location(api, code=_unique_code("WH1"), name="Warehouse 1")
        loc2 = _create_storage_location(api, code=_unique_code("WH2"), name="Warehouse 2")

        rt_url = mes_urls.get("rt", "http://localhost:5176")

        # 2. Go to RT Inventory Page
        await page.goto(rt_url)
        await page.get_by_role("button", name="Inventory").click()
        await expect(page.get_by_role("heading", name="Inventory", exact=True)).to_be_visible(timeout=10000)

        # 3. Create a Material Lot
        await page.get_by_role("button", name="Material Lots").click()
        await page.get_by_role("button", name="New Lot").click()

        # Dialog for new lot
```

## [OPEN] 2026-05-15T01:02:01Z - modules/SQA-RT/test_inventory_operations.py::test_rt_inventory_operations
- Summary: E   playwright._impl._errors.TimeoutError: Locator.select_option: Timeout 30000ms exceeded.
- First seen: 2026-05-15T01:02:01Z
- Last seen: 2026-05-15T01:02:01Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-RT\test_inventory_operations.py:129: in test_rt_inventory_operations
    await get_select("Material Lot").select_option(value=lot_id)
.venv\Lib\site-packages\playwright\async_api\_generated.py:18201: in select_option
    await self._impl_obj.select_option(
.venv\Lib\site-packages\playwright\_impl\_locator.py:610: in select_option
    return await self._frame.select_option(
.venv\Lib\site-packages\playwright\_impl\_frame.py:781: in select_option
    return await self._channel.send("selectOption", self._timeout, params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv\Lib\site-packages\playwright\_impl\_connection.py:69: in send
    return await self._connection.wrap_api_call(
.venv\Lib\site-packages\playwright\_impl\_connection.py:559: in wrap_api_call
    raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E   playwright._impl._errors.TimeoutError: Locator.select_option: Timeout 30000ms exceeded.
E   Call log:
E     - waiting for locator("label:has-text('Material Lot') ~ select:visible")
E       - locator resolved to <select required="" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">…</select>
E     - attempting select option action
E       2 × waiting for element to be visible and enabled
E         - did not find some options
E       - retrying select option action
E       - waiting 20ms
E       2 × waiting for element to be visible and enabled
E         - did not find some options
E       - retrying select option action
```

## [OPEN] 2026-05-15T15:41:10Z - modules/SQA-RT/test_inventory_operations.py::test_rt_inventory_operations
- Summary: E   AssertionError: Locator expected to have count '2'
- First seen: 2026-05-15T15:41:10Z
- Last seen: 2026-05-15T15:41:10Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-RT\test_inventory_operations.py:179: in test_rt_inventory_operations
    await expect(page.locator("tbody tr")).to_have_count(2, timeout=5000)
E   AssertionError: Locator expected to have count '2'
E   Actual value: 23
E   Call log:
E     - Expect "to_have_count" with timeout 5000ms
E     - waiting for locator("tbody tr")
E       3 × locator resolved to 22 elements
E         - unexpected value "22"
E       6 × locator resolved to 23 elements
E         - unexpected value "23"
```

## [OPEN] 2026-05-15T15:43:26Z - modules/SQA-RT/test_inventory_operations.py::test_rt_inventory_operations
- Summary: E   playwright._impl._errors.TimeoutError: Locator.fill: Timeout 30000ms exceeded.
- First seen: 2026-05-15T15:43:26Z
- Last seen: 2026-05-15T15:43:26Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-RT\test_inventory_operations.py:188: in test_rt_inventory_operations
    await page.get_by_placeholder("Filter by lot #").fill(lot_number)
.venv\Lib\site-packages\playwright\async_api\_generated.py:16552: in fill
    await self._impl_obj.fill(
.venv\Lib\site-packages\playwright\_impl\_locator.py:215: in fill
    return await self._frame.fill(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv\Lib\site-packages\playwright\_impl\_frame.py:607: in fill
    await self._fill(**locals_to_params(locals()))
.venv\Lib\site-packages\playwright\_impl\_frame.py:619: in _fill
    await self._channel.send("fill", self._timeout, locals_to_params(locals()))
.venv\Lib\site-packages\playwright\_impl\_connection.py:69: in send
    return await self._connection.wrap_api_call(
.venv\Lib\site-packages\playwright\_impl\_connection.py:559: in wrap_api_call
    raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E   playwright._impl._errors.TimeoutError: Locator.fill: Timeout 30000ms exceeded.
E   Call log:
E     - waiting for get_by_placeholder("Filter by lot #")
```

## [OPEN] 2026-05-15T15:48:09Z - modules/SQA-RT/test_inventory_operations.py::test_rt_inventory_operations
- Summary: E   AssertionError: Locator expected to contain text '80'
- First seen: 2026-05-15T15:48:09Z
- Last seen: 2026-05-15T15:48:09Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-RT\test_inventory_operations.py:112: in test_rt_inventory_operations
    await expect(page.locator("tr", has_text=loc1["code"])).to_contain_text("80")
E   AssertionError: Locator expected to contain text '80'
E   Actual value: LOT_fd3f50a5—WH2_a77815cb1300130
E   Call log:
E     - Expect "to_contain_text" with timeout 5000ms
E     - waiting for locator("tr").filter(has_text="WH2_a77815cb")
E       9 × locator resolved to <tr class="hover:bg-gray-50">…</tr>
E         - unexpected value "LOT_fd3f50a5—WH2_a77815cb1300130"
```

## [OPEN] 2026-05-15T15:50:54Z - modules/SQA-RT/test_inventory_operations.py::test_rt_inventory_operations
- Summary: E   AssertionError: Could not fetch balances: {"error":{"code":"VALIDATION_ERROR","message":"Request validation failed","details":{"errors":[{"type":"less_than_equal","loc":["query","limit"],"msg":"Input should be less than or equal to 200","input":"500","ctx":{"le":200}}]}},"meta":{"timestamp":"202
- First seen: 2026-05-15T15:50:54Z
- Last seen: 2026-05-15T15:50:54Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-RT\test_inventory_operations.py:40: in test_rt_inventory_operations
    assert resp.status_code == 200, f"Could not fetch balances: {resp.text}"
E   AssertionError: Could not fetch balances: {"error":{"code":"VALIDATION_ERROR","message":"Request validation failed","details":{"errors":[{"type":"less_than_equal","loc":["query","limit"],"msg":"Input should be less than or equal to 200","input":"500","ctx":{"le":200}}]}},"meta":{"timestamp":"2026-05-15T15:50:54.849781+00:00"}}
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Content]>.status_code
```

## [OPEN] 2026-05-15T15:51:25Z - modules/SQA-RT/test_inventory_operations.py::test_rt_inventory_operations
- Summary: E   AssertionError: Locator expected to be visible
- First seen: 2026-05-15T15:51:25Z
- Last seen: 2026-05-15T15:51:25Z
- Occurrences: 1
- Status: open
- Traceback excerpt:
```text
SQA\modules\SQA-RT\test_inventory_operations.py:130: in test_rt_inventory_operations
    await expect(page.locator("tbody tr").first).to_be_visible(timeout=5_000)
E   AssertionError: Locator expected to be visible
E   Actual value: hidden
E   Call log:
E     - Expect "to_be_visible" with timeout 5000ms
E     - waiting for locator("tbody tr").first
E       9 × locator resolved to <tr class="border-b hover:bg-gray-50">…</tr>
E         - unexpected value "hidden"
```

## [RESOLVED] 2026-05-15T15:55:44Z - modules/SQA-RT/test_inventory_operations.py::test_rt_inventory_operations
- Summary: E   AssertionError: Locator expected to be visible
- First seen: 2026-05-15T15:51:25Z
- Last seen failing run: 2026-05-15T15:51:25Z
- Occurrences before fix: 1
- Status: resolved
- Resolved at: 2026-05-15T15:55:44Z
