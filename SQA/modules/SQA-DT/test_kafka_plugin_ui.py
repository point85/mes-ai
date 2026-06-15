"""
SQA-DT — Kafka Java Bridge plugin configuration page UI tests.

Surfaces exercised:
  DT-CLIENT /plugins/kafka-java-bridge
  MES REST API /api/v1/plugins/kafka-java-bridge/*

Test groups:
  TestKafkaPluginPageLoad       — static elements always visible regardless of install state
  TestKafkaBuildPrerequisites   — Build Prerequisites card (jar/stubs status, Rebuild button)
  TestKafkaPluginInstall        — install form, config save, uninstall
  TestKafkaPluginEnableDisable  — enable / disable lifecycle (skipped if jar absent)
  TestKafkaConnectivityTest     — Test button (skipped unless plugin is running)

Markers:
  @pytest.mark.ui      — browser required
  @pytest.mark.slow    — some tests may take >30 s (enable + rebalance wait)

Environment:
  SQA_DT_URL     DT-CLIENT base URL  default http://localhost:5177
  SQA_SERVER_URL MES API base URL    default http://localhost:8082
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest
from playwright.async_api import Page, expect

_DT_BASE     = os.environ.get("SQA_DT_URL",     "http://localhost:5177")
_PLUGIN_URL  = f"{_DT_BASE}/plugins/kafka-java-bridge"
_PLUGIN_ID   = "kafka-java-bridge"
_API_PLUGIN  = f"/plugins/{_PLUGIN_ID}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _navigate(page: Page) -> None:
    """Navigate to the Kafka plugin detail page and wait for it to load."""
    await page.goto(_PLUGIN_URL)
    await expect(
        page.get_by_role("heading", name="Kafka Java SDK Bridge")
    ).to_be_visible(timeout=12_000)


def _api_plugin_detail(api) -> dict:
    resp = api.get(_API_PLUGIN)
    assert resp.status_code == 200, f"Could not fetch plugin: {resp.text}"
    return resp.json()["data"]


def _api_uninstall(api) -> None:
    resp = api.post(f"{_API_PLUGIN}/uninstall")
    assert resp.status_code in (200, 404), f"Uninstall failed: {resp.text}"


def _api_disable(api) -> None:
    api.post(f"{_API_PLUGIN}/disable")


# ---------------------------------------------------------------------------
# TestKafkaPluginPageLoad — elements present regardless of install state
# ---------------------------------------------------------------------------

@pytest.mark.ui
class TestKafkaPluginPageLoad:

    async def test_page_title_and_plugin_id_shown(self, page: Page) -> None:
        await _navigate(page)
        # Plugin name heading
        await expect(
            page.get_by_role("heading", name="Kafka Java SDK Bridge")
        ).to_be_visible()
        # Plugin ID in subtitle
        await expect(
            page.locator("text=kafka-java-bridge")
        ).to_be_visible()

    async def test_version_shown_in_subtitle(self, page: Page) -> None:
        await _navigate(page)
        # The subtitle paragraph contains "v1.0.0"
        await expect(
            page.locator("p").filter(has_text="v1.0.0").first
        ).to_be_visible()

    async def test_status_badge_visible(self, page: Page) -> None:
        await _navigate(page)
        # The status badge is a rounded-full span containing one of the known states
        for state in ("available", "disabled", "running", "stopped", "error"):
            candidate = page.locator("span").filter(has_text=state).first
            if await candidate.is_visible():
                return
        pytest.fail("No recognisable status badge found on plugin page")

    async def test_back_navigation_returns_to_plugin_list(self, page: Page) -> None:
        await _navigate(page)
        # The back arrow button has a unique class combination "rounded p-1"
        await page.locator("button.rounded.p-1").click()
        await expect(page).to_have_url(f"{_DT_BASE}/plugins", timeout=8_000)

    async def test_build_prerequisites_card_visible(self, page: Page) -> None:
        await _navigate(page)
        await expect(
            page.get_by_text("Build Prerequisites")
        ).to_be_visible(timeout=8_000)

    async def test_description_info_card_present(self, page: Page) -> None:
        await _navigate(page)
        await expect(page.get_by_text("Description")).to_be_visible()

    async def test_category_shown_as_equipment(self, page: Page) -> None:
        await _navigate(page)
        # The Category info card renders "equipment" in a <dd> element
        await expect(
            page.locator("dd").filter(has_text="equipment").first
        ).to_be_visible()


# ---------------------------------------------------------------------------
# TestKafkaBuildPrerequisites — Build Prerequisites card
# ---------------------------------------------------------------------------

@pytest.mark.ui
class TestKafkaBuildPrerequisites:

    async def test_prerequisites_card_heading(self, page: Page) -> None:
        await _navigate(page)
        await expect(
            page.get_by_text("Build Prerequisites")
        ).to_be_visible(timeout=8_000)

    async def test_jar_status_row_visible(self, page: Page) -> None:
        await _navigate(page)
        # "Java fat-jar:" label appears in the status rows
        await expect(
            page.get_by_text("Java fat-jar:", exact=False)
        ).to_be_visible(timeout=10_000)

    async def test_stubs_status_row_visible(self, page: Page) -> None:
        await _navigate(page)
        await expect(
            page.get_by_text("Python gRPC stubs:", exact=False)
        ).to_be_visible(timeout=10_000)

    async def test_maven_status_row_visible(self, page: Page) -> None:
        await _navigate(page)
        await expect(
            page.get_by_text("Maven:", exact=False)
        ).to_be_visible(timeout=10_000)

    async def test_rebuild_button_always_present(self, page: Page) -> None:
        await _navigate(page)
        await expect(
            page.get_by_role("button", name="Rebuild")
        ).to_be_visible(timeout=10_000)

    async def test_rebuild_button_shows_rebuilding_while_pending(
        self, page: Page, api
    ) -> None:
        """Clicking Rebuild should briefly show 'Rebuilding…' (or complete immediately
        if jar+stubs already exist).  We intercept the POST to make it stall."""
        await _navigate(page)
        # Stall the prepare POST so the button stays in pending state.
        # Use a short sleep (1 s) then abort.  IMPORTANT: after asserting the
        # pending label we wait 1.5 s so the handler fully completes inside this
        # test function.  This prevents the asyncio.sleep task from leaking into
        # the next test on the shared session-scoped event loop.
        async def _stall(route):
            await asyncio.sleep(1)
            await route.abort()

        await page.route("**/plugins/kafka-java-bridge/prepare**", _stall)
        rebuild_btn = page.get_by_role("button", name="Rebuild")
        await expect(rebuild_btn).to_be_visible(timeout=10_000)
        await rebuild_btn.click()
        await expect(
            page.get_by_role("button", name="Rebuilding…")
        ).to_be_visible(timeout=3_000)
        # Wait for the stall handler to finish before this test returns.
        await asyncio.sleep(1.5)
        await page.unroute("**/plugins/kafka-java-bridge/prepare**")

    async def test_build_and_generate_button_shown_when_artifacts_missing(
        self, page: Page, api
    ) -> None:
        """Mock the status endpoint to report missing jar so the primary button appears."""
        async def _missing_status(route):
            await route.fulfill(
                status=200,
                content_type="application/json",
                body='{"data":{"jar_exists":false,"jar_path":"/fake","stubs_exist":false,"mvn_path":null}}',
            )

        # Register mock before navigation so the status response is already
        # intercepted when React Query fires the status request on mount.
        await page.route("**/plugins/kafka-java-bridge/status", _missing_status)
        await _navigate(page)
        await expect(
            page.get_by_role("button", name="Build & Generate")
        ).to_be_visible(timeout=8_000)
        await page.unroute("**/plugins/kafka-java-bridge/status")


# ---------------------------------------------------------------------------
# TestKafkaPluginInstall — install / config / uninstall flow
# ---------------------------------------------------------------------------

@pytest.mark.ui
class TestKafkaPluginInstall:

    @pytest.fixture(autouse=True)
    async def ensure_uninstalled(self, api) -> None:
        """Guarantee the plugin starts each test in an uninstalled state."""
        _api_disable(api)
        _api_uninstall(api)
        yield
        _api_disable(api)
        _api_uninstall(api)

    async def test_install_form_shown_when_not_installed(self, page: Page) -> None:
        await _navigate(page)
        # The "Plugin Parameters" section heading appears for uninstalled plugins
        await expect(
            page.get_by_text("Plugin Parameters")
        ).to_be_visible(timeout=8_000)

    async def test_config_fields_present(self, page: Page) -> None:
        await _navigate(page)
        await expect(page.get_by_text("Plugin Parameters")).to_be_visible(timeout=8_000)
        # formatLabel() title-cases snake_case names; use exact=True to avoid
        # matching parameter description text that contains the same words.
        for label in ("Bootstrap Servers", "Bridge Port", "Consumer Group"):
            await expect(page.get_by_text(label, exact=True)).to_be_visible()

    async def test_bridge_jar_field_not_shown(self, page: Page) -> None:
        """bridge_jar is auto-computed server-side and hidden from the UI."""
        await _navigate(page)
        await expect(page.get_by_text("Plugin Parameters")).to_be_visible(timeout=8_000)
        bridge_jar_label = page.get_by_text("bridge_jar", exact=True)
        await expect(bridge_jar_label).not_to_be_visible()

    async def test_install_button_visible_after_filling_required_fields(
        self, page: Page, api
    ) -> None:
        """Mock the status endpoint to report jar+stubs present so Install appears."""
        async def _ready_status(route):
            await route.fulfill(
                status=200,
                content_type="application/json",
                body='{"data":{"jar_exists":true,"jar_path":"/fake/kafka-bridge.jar","stubs_exist":true,"mvn_path":"/usr/bin/mvn"}}',
            )

        await page.route("**/plugins/kafka-java-bridge/status", _ready_status)
        await _navigate(page)
        await expect(page.get_by_text("Plugin Parameters")).to_be_visible(timeout=8_000)
        # The Install button is shown below the parameter form
        await expect(
            page.get_by_role("button", name="Install")
        ).to_be_visible(timeout=8_000)
        await page.unroute("**/plugins/kafka-java-bridge/status")

    async def test_save_configuration_button_shown_when_installed(
        self, page: Page, api
    ) -> None:
        """Install via API, then verify UI shows 'Save Configuration'."""
        detail = _api_plugin_detail(api)
        if not detail.get("installed"):
            # Install via API — fill only non-auto params
            resp = api.post(
                f"{_API_PLUGIN}/install",
                json={
                    "parameter_values": {
                        "bootstrap_servers": "localhost:9092",
                        "bridge_port":       "50053",
                        "consumer_group":    "sqa-test-group",
                    }
                },
            )
            if resp.status_code not in (200, 201):
                pytest.skip(f"Could not install plugin via API: {resp.text}")

        await _navigate(page)
        await expect(
            page.get_by_role("heading", name="Configuration")
        ).to_be_visible(timeout=8_000)
        await expect(
            page.get_by_role("button", name="Save Configuration")
        ).to_be_visible(timeout=8_000)

    async def test_save_configuration_button_disabled_until_changed(
        self, page: Page, api
    ) -> None:
        detail = _api_plugin_detail(api)
        if not detail.get("installed"):
            pytest.skip("Plugin not installed — cannot test config save state")

        await _navigate(page)
        save_btn = page.get_by_role("button", name="Save Configuration")
        await expect(save_btn).to_be_visible(timeout=8_000)
        await expect(save_btn).to_be_disabled()

        # Edit a field to make the form dirty
        bootstrap_input = page.locator("input").filter(
            has=page.locator("..").filter(has_text="bootstrap_servers")
        ).first
        # Fallback: find by placeholder or value
        all_inputs = page.locator("input[type='text'], input:not([type])")
        count = await all_inputs.count()
        if count > 0:
            await all_inputs.first.click()
            await all_inputs.first.press("End")
            await all_inputs.first.type(" ")
            await expect(save_btn).to_be_enabled(timeout=3_000)

    async def test_uninstall_button_visible_when_installed(
        self, page: Page, api
    ) -> None:
        detail = _api_plugin_detail(api)
        if not detail.get("installed"):
            pytest.skip("Plugin not installed — skipping uninstall button check")

        await _navigate(page)
        await expect(
            page.get_by_role("button", name="Uninstall")
        ).to_be_visible(timeout=8_000)


# ---------------------------------------------------------------------------
# TestKafkaPluginEnableDisable
# ---------------------------------------------------------------------------

@pytest.mark.ui
@pytest.mark.slow
class TestKafkaPluginEnableDisable:

    @pytest.fixture(autouse=True)
    async def ensure_installed_disabled(self, api) -> None:
        """Ensure installed but disabled before each test."""
        detail = _api_plugin_detail(api)
        if not detail.get("installed"):
            pytest.skip("Plugin not installed — skipping enable/disable tests")
        _api_disable(api)
        yield
        _api_disable(api)

    async def test_enable_button_visible_when_disabled(self, page: Page) -> None:
        await _navigate(page)
        await expect(
            page.get_by_role("button", name="Enable")
        ).to_be_visible(timeout=8_000)

    async def test_disable_button_visible_when_running(
        self, page: Page, api
    ) -> None:
        detail = _api_plugin_detail(api)
        if not detail.get("installed"):
            pytest.skip("Not installed")

        # Check if jar exists; skip enable attempt if not
        status_resp = api.get("/plugins/kafka-java-bridge/status")
        if status_resp.status_code != 200:
            pytest.skip("Cannot fetch bridge status")
        bridge_status = status_resp.json()["data"]
        if not bridge_status.get("jar_exists"):
            pytest.skip("Jar not built — cannot enable plugin")

        # Enable via API
        resp = api.post(f"{_API_PLUGIN}/enable")
        if resp.status_code != 200:
            pytest.skip(f"Could not enable plugin via API: {resp.text}")

        await _navigate(page)
        await expect(
            page.get_by_role("button", name="Disable")
        ).to_be_visible(timeout=15_000)

    async def test_test_button_visible_when_running(
        self, page: Page, api
    ) -> None:
        detail = _api_plugin_detail(api)
        if not detail.get("is_running"):
            pytest.skip("Plugin not running — Test button not shown")

        await _navigate(page)
        await expect(
            page.get_by_role("button", name="Test")
        ).to_be_visible(timeout=8_000)

    async def test_enable_error_banner_shown_on_failure(
        self, page: Page, api
    ) -> None:
        """Mock the enable endpoint to return an error, verify the banner appears."""
        await _navigate(page)

        async def _enable_error(route):
            await route.fulfill(
                status=500,
                content_type="application/json",
                body='{"detail":"Kafka bridge jar not found"}',
            )

        await page.route(
            f"**/plugins/{_PLUGIN_ID}/enable",
            _enable_error,
        )
        enable_btn = page.get_by_role("button", name="Enable")
        await expect(enable_btn).to_be_visible(timeout=8_000)
        await enable_btn.click()
        await expect(
            page.get_by_text("Enable failed:", exact=False)
        ).to_be_visible(timeout=8_000)
        await page.unroute(f"**/plugins/{_PLUGIN_ID}/enable")


# ---------------------------------------------------------------------------
# TestKafkaConnectivityTest — Test button (requires running plugin + live Kafka)
# ---------------------------------------------------------------------------

@pytest.mark.ui
@pytest.mark.slow
class TestKafkaConnectivityTest:

    @pytest.fixture(autouse=True)
    async def skip_unless_running(self, api) -> None:
        detail = _api_plugin_detail(api)
        if not detail.get("is_running"):
            pytest.skip("Plugin not running — connectivity test UI tests skipped")
        yield

    async def test_test_button_present(self, page: Page) -> None:
        await _navigate(page)
        await expect(
            page.get_by_role("button", name="Test")
        ).to_be_visible(timeout=8_000)

    async def test_test_button_shows_testing_while_pending(
        self, page: Page
    ) -> None:
        """Stall the test endpoint so the 'Testing…' label is observable."""
        await _navigate(page)

        async def _stall(route):
            pass  # never fulfil

        await page.route("**/plugins/kafka-java-bridge/test", _stall)
        test_btn = page.get_by_role("button", name="Test")
        await expect(test_btn).to_be_visible(timeout=8_000)
        await test_btn.click()
        await expect(
            page.get_by_role("button", name="Testing…")
        ).to_be_visible(timeout=5_000)
        await page.unroute("**/plugins/kafka-java-bridge/test")

    async def test_success_banner_shown_on_pass(self, page: Page) -> None:
        """Mock the test endpoint to return a success payload."""
        await _navigate(page)

        async def _success(route):
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=(
                    '{"data":{"topic":"mes-bridge-test-abc12345",'
                    '"sent":"MES Kafka round-trip test 1234567890.0",'
                    '"received":"MES Kafka round-trip test 1234567890.0",'
                    '"match":true}}'
                ),
            )

        await page.route("**/plugins/kafka-java-bridge/test", _success)
        test_btn = page.get_by_role("button", name="Test")
        await expect(test_btn).to_be_visible(timeout=8_000)
        await test_btn.click()
        await expect(
            page.get_by_text("Test passed.", exact=False)
        ).to_be_visible(timeout=8_000)
        await expect(
            page.get_by_text("mes-bridge-test-abc12345", exact=False)
        ).to_be_visible()
        await page.unroute("**/plugins/kafka-java-bridge/test")

    async def test_error_banner_shown_on_failure(self, page: Page) -> None:
        """Mock the test endpoint to return a 502 error."""
        await _navigate(page)

        async def _error(route):
            await route.fulfill(
                status=502,
                content_type="application/json",
                body='{"detail":"Timed out after 35s waiting for message on \'mes-bridge-test-xyz\'"}',
            )

        await page.route("**/plugins/kafka-java-bridge/test", _error)
        test_btn = page.get_by_role("button", name="Test")
        await expect(test_btn).to_be_visible(timeout=8_000)
        await test_btn.click()
        await expect(
            page.get_by_text("Test failed:", exact=False)
        ).to_be_visible(timeout=8_000)
        await page.unroute("**/plugins/kafka-java-bridge/test")

    @pytest.mark.slow
    async def test_live_round_trip(self, page: Page) -> None:
        """
        End-to-end round-trip against a real running Kafka broker.

        This test does NOT mock anything.  It clicks Test, waits up to 45 s
        (allowing 35 s for the backend + network latency), and asserts the
        'Test passed.' banner appears.

        Skipped automatically by the skip_unless_running fixture if the plugin
        is not running.
        """
        await _navigate(page)
        test_btn = page.get_by_role("button", name="Test")
        await expect(test_btn).to_be_visible(timeout=8_000)
        await test_btn.click()
        # Wait generously — the backend waits 5 s for rebalance + message transit
        await expect(
            page.get_by_text("Test passed.", exact=False)
        ).to_be_visible(timeout=45_000)
