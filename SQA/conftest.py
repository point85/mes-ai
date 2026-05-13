"""
SQA root conftest.py — session-scoped fixtures shared across all SQA modules.

Environment variables (with defaults):
  SQA_SERVER_URL   MES API base URL        default: http://localhost:8081
  SQA_DT_URL       DT-CLIENT base URL      default: http://localhost:5177
  SQA_HEADED       Set to "1" for headed browser (useful for local debug)
"""
from __future__ import annotations

import os
import pytest
import httpx
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# ---------------------------------------------------------------------------
# URL configuration
# ---------------------------------------------------------------------------
SERVER_URL = os.environ.get("SQA_SERVER_URL", "http://localhost:8081")
DT_URL     = os.environ.get("SQA_DT_URL",     "http://localhost:5177")
HEADED     = os.environ.get("SQA_HEADED", "0") == "1"

API_BASE   = f"{SERVER_URL}/api/v1"


# ---------------------------------------------------------------------------
# mes_urls — dict of all surface base URLs
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def mes_urls() -> dict[str, str]:
    return {
        "server": SERVER_URL,
        "api":    API_BASE,
        "dt":     DT_URL,
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
# uom_cleanup — delete all SQA_* test UoMs after each test
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=False)
def uom_cleanup(api):
    """Delete any UoM rows whose symbol starts with 'SQA_' before and after the test."""
    def _delete_sqa_uoms():
        resp = api.get("/uom", params={"limit": "200"})
        if resp.status_code != 200:
            return
        items = resp.json().get("data", [])
        for uom in items:
            if uom.get("symbol", "").startswith("SQA_"):
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
