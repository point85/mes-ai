"""
SQA root conftest.py — session-scoped fixtures shared across all SQA modules.

Environment variables (with defaults):
  SQA_SERVER_URL   MES API base URL        default: http://localhost:8081
  SQA_DT_URL       DT-CLIENT base URL      default: http://localhost:5177
  SQA_HEADED       Set to "1" for headed browser (useful for local debug)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
import httpx
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# ---------------------------------------------------------------------------
# URL configuration
# ---------------------------------------------------------------------------
SERVER_URL = os.environ.get("SQA_SERVER_URL", "http://localhost:8081")
DT_URL     = os.environ.get("SQA_DT_URL",     "http://localhost:5177")
RT_URL     = os.environ.get("SQA_RT_URL",     "http://localhost:5176")
HEADED     = os.environ.get("SQA_HEADED", "0") == "1"

API_BASE   = f"{SERVER_URL}/api/v1"
SQA_ROOT   = Path(__file__).resolve().parent
REPO_ROOT  = SQA_ROOT.parent
DEFECT_LOG_PATH = REPO_ROOT / "docs" / "DEFECT_LOG.md"
DEFECT_STATE_PATH = SQA_ROOT / ".defect_state.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_defect_state() -> dict:
    if not DEFECT_STATE_PATH.exists():
        return {"open_defects": {}}

    try:
        return json.loads(DEFECT_STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"open_defects": {}}


def _write_defect_state(state: dict) -> None:
    DEFECT_STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _ensure_defect_log() -> None:
    if DEFECT_LOG_PATH.exists():
        return

    DEFECT_LOG_PATH.write_text(
        "# Defect Log\n\n"
        "> Running log of defects discovered by SQA tests and later confirmed fixed.\n\n"
        "Entries are appended automatically by the shared pytest harness in SQA/conftest.py.\n",
        encoding="utf-8",
    )


def _append_defect_log(entry: str) -> None:
    _ensure_defect_log()
    with DEFECT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"\n{entry}\n")


def _normalize_longrepr(longrepr) -> str:
    if longrepr is None:
        return ""
    text = str(longrepr).strip()
    if not text:
        return ""
    return "\n".join(line.rstrip() for line in text.splitlines()[:25])


def _summarize_failure(longrepr_text: str) -> str:
    if not longrepr_text:
        return "Test failed without a captured traceback."

    lines = [line.strip() for line in longrepr_text.splitlines() if line.strip()]
    if not lines:
        return "Test failed without a captured traceback."

    for line in reversed(lines):
        if any(token in line for token in ("AssertionError", "Error", "Exception", "Failed")):
            return line[:300]
    return lines[-1][:300]


def _make_failure_signature(nodeid: str, summary: str) -> str:
    normalized = " ".join(summary.split())
    return f"{nodeid}::{normalized}"


def _record_new_defect(nodeid: str, summary: str, traceback_text: str) -> None:
    state = _read_defect_state()
    open_defects = state.setdefault("open_defects", {})
    signature = _make_failure_signature(nodeid, summary)
    timestamp = _utc_now()

    existing = open_defects.get(nodeid)
    if existing and existing.get("signature") == signature:
        existing["last_seen"] = timestamp
        existing["occurrences"] = int(existing.get("occurrences", 1)) + 1
        _write_defect_state(state)
        return

    open_defects[nodeid] = {
        "signature": signature,
        "summary": summary,
        "first_seen": timestamp,
        "last_seen": timestamp,
        "occurrences": 1,
        "traceback": traceback_text,
    }
    _write_defect_state(state)

    _append_defect_log(
        "## [OPEN] {timestamp} - {nodeid}\n"
        "- Summary: {summary}\n"
        "- First seen: {timestamp}\n"
        "- Last seen: {timestamp}\n"
        "- Occurrences: 1\n"
        "- Status: open\n"
        "- Traceback excerpt:\n"
        "```text\n{traceback}\n```".format(
            timestamp=timestamp,
            nodeid=nodeid,
            summary=summary,
            traceback=traceback_text or "No traceback captured.",
        )
    )


def _resolve_defect(nodeid: str) -> None:
    state = _read_defect_state()
    open_defects = state.setdefault("open_defects", {})
    existing = open_defects.pop(nodeid, None)
    if not existing:
        return

    resolved_at = _utc_now()
    _write_defect_state(state)

    _append_defect_log(
        "## [RESOLVED] {resolved_at} - {nodeid}\n"
        "- Summary: {summary}\n"
        "- First seen: {first_seen}\n"
        "- Last seen failing run: {last_seen}\n"
        "- Occurrences before fix: {occurrences}\n"
        "- Status: resolved\n"
        "- Resolved at: {resolved_at}".format(
            resolved_at=resolved_at,
            nodeid=nodeid,
            summary=existing.get("summary", "Unknown failure"),
            first_seen=existing.get("first_seen", "unknown"),
            last_seen=existing.get("last_seen", "unknown"),
            occurrences=existing.get("occurrences", 1),
        )
    )


def pytest_sessionstart(session) -> None:
    _ensure_defect_log()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"_report_{report.when}", report)


def pytest_runtest_teardown(item, nextitem) -> None:
    call_report = getattr(item, "_report_call", None)
    if call_report is None:
        return

    if call_report.failed:
        traceback_text = _normalize_longrepr(call_report.longrepr)
        summary = _summarize_failure(traceback_text)
        _record_new_defect(item.nodeid, summary, traceback_text)
    elif call_report.passed:
        _resolve_defect(item.nodeid)


# ---------------------------------------------------------------------------
# mes_urls — dict of all surface base URLs
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def mes_urls() -> dict[str, str]:
    return {
        "server": SERVER_URL,
        "api":    API_BASE,
        "dt":     DT_URL,
        "rt":     RT_URL,
    }


# ---------------------------------------------------------------------------
# api — synchronous httpx client for API oracles
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def api():
    """Authenticated (auth=none) httpx client pointed at the MES API."""
    with httpx.Client(base_url=API_BASE, timeout=15) as client:
        yield client


# ---------------------------------------------------------------------------
# api_async — async httpx client (for use inside async tests)
# ---------------------------------------------------------------------------
@pytest.fixture
async def api_async():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=15) as client:
        yield client


# ---------------------------------------------------------------------------
# browser / browser_context / page — Playwright fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
async def browser():
    async with async_playwright() as pw:
        b: Browser = await pw.chromium.launch(headless=not HEADED)
        yield b
        await b.close()


@pytest.fixture
async def browser_context(browser: Browser) -> BrowserContext:
    ctx: BrowserContext = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        base_url=DT_URL,
    )
    yield ctx
    await ctx.close()


@pytest.fixture
async def page(browser_context: BrowserContext) -> Page:
    p: Page = await browser_context.new_page()
    yield p
    await p.close()


# ---------------------------------------------------------------------------
# uom_cleanup — delete all SQA* test UoMs after each test
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=False)
def uom_cleanup(api):
    """Delete any UoM rows whose symbol starts with 'SQA' before and after the test."""
    def _delete_sqa_uoms():
        resp = api.get("/uom", params={"limit": "200"})
        if resp.status_code != 200:
            return
        items = resp.json().get("data", [])
        for uom in items:
            if uom.get("symbol", "").startswith("SQA"):
                api.delete(f"/uom/{uom['id']}")

    _delete_sqa_uoms()   # pre-test cleanup (idempotent)
    yield
    _delete_sqa_uoms()   # post-test cleanup


# ---------------------------------------------------------------------------
# data_definition_cleanup -- delete all SQA_DD_* test definitions
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=False)
def data_definition_cleanup(api):
    """Delete any data definitions whose code starts with 'SQA_DD_' before and after the test."""

    def _delete_sqa_data_definitions():
        resp = api.get("/data/definitions", params={"limit": "200"})
        if resp.status_code != 200:
            return
        items = resp.json().get("data", [])
        for definition in items:
            if definition.get("code", "").startswith("SQA_DD_"):
                api.delete(f"/data/definitions/{definition['id']}")

    _delete_sqa_data_definitions()
    yield
    _delete_sqa_data_definitions()


def _delete_sqa_routes(api) -> None:
    routes_resp = api.get("/operations-definitions", params={"limit": "200"})
    if routes_resp.status_code != 200:
        return

    for route in routes_resp.json().get("data", []):
        if route.get("name", "").startswith("SQA"):
            api.delete(f"/operations-definitions/{route['id']}")


# ---------------------------------------------------------------------------
# route_cleanup -- delete all SQA* standalone/test routes
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=False)
def route_cleanup(api):
    """Delete any active routes whose name starts with 'SQA' before and after the test."""

    _delete_sqa_routes(api)
    yield
    _delete_sqa_routes(api)


# ---------------------------------------------------------------------------
# product_cleanup -- delete all SQA_PROD_* test products
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=False)
def product_cleanup(api):
    """Delete any products whose code starts with 'SQA_PROD_' before and after the test."""

    def _delete_sqa_products():
        _delete_sqa_routes(api)

        resp = api.get("/products", params={"limit": "200"})
        if resp.status_code != 200:
            return
        items = resp.json().get("data", [])
        for product in items:
            if product.get("code", "").startswith("SQA_PROD_"):
                product_routes_resp = api.get(
                    f"/products/{product['id']}/operations-definitions",
                    params={"limit": "200"},
                )
                if product_routes_resp.status_code == 200:
                    for route in product_routes_resp.json().get("data", []):
                        if route.get("name", "").startswith("SQA"):
                            api.delete(f"/operations-definitions/{route['id']}")
                api.delete(f"/products/{product['id']}")

    _delete_sqa_products()
    yield
    _delete_sqa_products()


# ---------------------------------------------------------------------------
# material_cleanup -- delete all SQA_MAT_* test materials
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=False)
def material_cleanup(api):
    """Delete any materials whose code starts with 'SQA_MAT_' before and after the test."""

    def _delete_sqa_materials():
        resp = api.get("/materials", params={"limit": "200"})
        if resp.status_code != 200:
            return
        items = resp.json().get("data", [])
        for material in items:
            if material.get("code", "").startswith("SQA_MAT_"):
                api.delete(f"/materials/{material['id']}")

    _delete_sqa_materials()
    yield
    _delete_sqa_materials()


# ---------------------------------------------------------------------------
# physical_model_cleanup -- delete SQA physical-model hierarchy entities
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=False)
def physical_model_cleanup(api):
    """Delete SQA physical-model entities in reverse hierarchy order before and after a test."""

    def _delete_sqa_physical_model():
        equipment_resp = api.get("/equipment", params={"limit": "200"})
        if equipment_resp.status_code == 200:
            for equipment in equipment_resp.json().get("data", []):
                if equipment.get("code", "").startswith("SQA_EQ_"):
                    api.delete(f"/equipment/{equipment['id']}")

        wc_resp = api.get("/work-cells", params={"limit": "200"})
        if wc_resp.status_code == 200:
            for work_cell in wc_resp.json().get("data", []):
                if work_cell.get("code", "").startswith("SQA_WC_"):
                    api.delete(f"/work-cells/{work_cell['id']}")

        lines_resp = api.get("/lines", params={"limit": "200"})
        if lines_resp.status_code == 200:
            for line in lines_resp.json().get("data", []):
                if line.get("code", "").startswith("SQA_LN_"):
                    api.delete(f"/lines/{line['id']}")

        sites_resp = api.get("/sites", params={"limit": "200"})
        if sites_resp.status_code == 200:
            sites = sites_resp.json().get("data", [])
            for site in sites:
                if site.get("code", "").startswith("SQA_ST_"):
                    areas_resp = api.get(f"/sites/{site['id']}/areas", params={"limit": "200"})
                    if areas_resp.status_code == 200:
                        for area in areas_resp.json().get("data", []):
                            if area.get("code", "").startswith("SQA_AR_"):
                                api.delete(f"/areas/{area['id']}")
                    api.delete(f"/sites/{site['id']}")

    _delete_sqa_physical_model()
    yield
    _delete_sqa_physical_model()


# ---------------------------------------------------------------------------
# reason_cleanup -- delete SQA reason-code hierarchy rows
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=False)
def reason_cleanup(api):
    """Delete SQA reason codes in child-first order before and after a test."""

    def _is_sqa_reason(reason: dict) -> bool:
        name = reason.get("name") or ""
        description = reason.get("description") or ""
        return name.startswith("SQA ") or description.startswith("SQA ")

    def _delete_sqa_reasons():
        resp = api.get("/performance/reasons")
        if resp.status_code != 200:
            return

        items = resp.json().get("data", [])
        sqa_reasons = [item for item in items if _is_sqa_reason(item)]
        if not sqa_reasons:
            return

        by_id = {item["id"]: item for item in sqa_reasons}

        def _depth(reason: dict) -> int:
            depth = 0
            parent_id = reason.get("parent_id")
            while parent_id and parent_id in by_id:
                depth += 1
                parent_id = by_id[parent_id].get("parent_id")
            return depth

        for reason in sorted(sqa_reasons, key=_depth, reverse=True):
            api.delete(f"/performance/reasons/{reason['id']}")

    _delete_sqa_reasons()
    yield
    _delete_sqa_reasons()


# ---------------------------------------------------------------------------
# auth_admin_cleanup -- delete SQA auth users and custom roles
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=False)
def auth_admin_cleanup(api):
    """Delete SQA auth users and custom roles before and after a test."""

    def _delete_sqa_auth_data():
        users_resp = api.get("/auth/users")
        if users_resp.status_code == 200:
            for user in users_resp.json().get("data", []):
                if user.get("username", "").startswith("sqa-auth-user-"):
                    api.delete(f"/auth/users/{user['id']}")

        roles_resp = api.get("/auth/roles")
        if roles_resp.status_code == 200:
            for role in roles_resp.json().get("data", []):
                if role.get("name", "").startswith("SQA_ROLE_"):
                    api.delete(f"/auth/roles/{role['id']}")

    _delete_sqa_auth_data()
    yield
    _delete_sqa_auth_data()
