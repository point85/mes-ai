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
