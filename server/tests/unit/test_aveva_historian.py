"""
Unit tests for AVEVA Historian REST API Adapter.

All tests use mocking — no real AVEVA Historian server is required.
Tests cover: AVEVAHistorianSettings, AVEVAHistorianClient,
AVEVAHistorianAdapter lifecycle/reads/subscriptions/state,
AVEVAHistorianPlugin integration, and manifest validation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml


# ═══════════════════════════════════════════════════════════════════════════
#  Config Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAVEVAHistorianSettings:
    """Verify AVEVAHistorianSettings defaults and custom values."""

    def test_defaults(self):
        from mes.adapters.historian.aveva.config import AVEVAHistorianSettings

        s = AVEVAHistorianSettings(_env_file=None)
        assert s.AVEVA_BASE_URL == ""
        assert s.AVEVA_AUTH_MODE == "negotiate"
        assert s.AVEVA_USERNAME == ""
        assert s.AVEVA_PASSWORD == ""
        assert s.AVEVA_BEARER_TOKEN == ""
        assert s.AVEVA_VERIFY_SSL is True
        assert s.AVEVA_TIMEOUT_SEC == 30
        assert s.AVEVA_DATASOURCE == ""
        assert s.AVEVA_EQUIPMENT_ID == ""
        assert s.AVEVA_TAG_PREFIX == ""
        assert s.AVEVA_STATE_TAG_FQN == ""
        assert s.AVEVA_STATE_MODEL_ID == ""
        assert s.AVEVA_POLL_INTERVAL_SEC == 5

    def test_custom_values(self):
        from mes.adapters.historian.aveva.config import AVEVAHistorianSettings

        s = AVEVAHistorianSettings(
            _env_file=None,
            AVEVA_BASE_URL="http://historian:32569/Historian/v2",
            AVEVA_AUTH_MODE="bearer",
            AVEVA_USERNAME="DOMAIN\\user",
            AVEVA_PASSWORD="s3cret",
            AVEVA_BEARER_TOKEN="eyJhbGciOiJSUzI1NiJ9.test",
            AVEVA_VERIFY_SSL=False,
            AVEVA_TIMEOUT_SEC=60,
            AVEVA_DATASOURCE="Baytown",
            AVEVA_EQUIPMENT_ID="abc-123",
            AVEVA_TAG_PREFIX="Baytown.Line1_",
            AVEVA_STATE_TAG_FQN="Baytown.Line1_State",
            AVEVA_STATE_MODEL_ID="packml",
            AVEVA_POLL_INTERVAL_SEC=10,
        )
        assert s.AVEVA_BASE_URL == "http://historian:32569/Historian/v2"
        assert s.AVEVA_AUTH_MODE == "bearer"
        assert s.AVEVA_USERNAME == "DOMAIN\\user"
        assert s.AVEVA_BEARER_TOKEN == "eyJhbGciOiJSUzI1NiJ9.test"
        assert s.AVEVA_VERIFY_SSL is False
        assert s.AVEVA_TIMEOUT_SEC == 60
        assert s.AVEVA_DATASOURCE == "Baytown"
        assert s.AVEVA_EQUIPMENT_ID == "abc-123"
        assert s.AVEVA_TAG_PREFIX == "Baytown.Line1_"
        assert s.AVEVA_STATE_TAG_FQN == "Baytown.Line1_State"
        assert s.AVEVA_STATE_MODEL_ID == "packml"
        assert s.AVEVA_POLL_INTERVAL_SEC == 10

    def test_timeout_minimum_validation(self):
        from pydantic import ValidationError
        from mes.adapters.historian.aveva.config import AVEVAHistorianSettings

        with pytest.raises(ValidationError):
            AVEVAHistorianSettings(_env_file=None, AVEVA_TIMEOUT_SEC=0)

    def test_poll_interval_minimum_validation(self):
        from pydantic import ValidationError
        from mes.adapters.historian.aveva.config import AVEVAHistorianSettings

        with pytest.raises(ValidationError):
            AVEVAHistorianSettings(_env_file=None, AVEVA_POLL_INTERVAL_SEC=0)


# ═══════════════════════════════════════════════════════════════════════════
#  Client Helper Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestClientHelpers:
    """Test standalone helper functions in the client module."""

    def test_opc_quality_to_str_good(self):
        from mes.adapters.historian.aveva.client import _opc_quality_to_str

        assert _opc_quality_to_str(192) == "good"
        assert _opc_quality_to_str(200) == "good"
        assert _opc_quality_to_str(255) == "good"

    def test_opc_quality_to_str_uncertain(self):
        from mes.adapters.historian.aveva.client import _opc_quality_to_str

        assert _opc_quality_to_str(64) == "uncertain"
        assert _opc_quality_to_str(100) == "uncertain"
        assert _opc_quality_to_str(191) == "uncertain"

    def test_opc_quality_to_str_bad(self):
        from mes.adapters.historian.aveva.client import _opc_quality_to_str

        assert _opc_quality_to_str(0) == "bad"
        assert _opc_quality_to_str(63) == "bad"

    def test_to_iso_utc_aware(self):
        from mes.adapters.historian.aveva.client import _to_iso_utc

        dt = datetime(2025, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        result = _to_iso_utc(dt)
        assert result == "2025-06-15T12:30:00.000000Z"

    def test_to_iso_utc_naive(self):
        from mes.adapters.historian.aveva.client import _to_iso_utc

        dt = datetime(2025, 6, 15, 12, 30, 0)
        result = _to_iso_utc(dt)
        assert result == "2025-06-15T12:30:00.000000Z"

    def test_encode_fqn_plain(self):
        from mes.adapters.historian.aveva.client import _encode_fqn

        assert _encode_fqn("Baytown.tank_level") == "Baytown.tank_level"

    def test_encode_fqn_single_quotes(self):
        from mes.adapters.historian.aveva.client import _encode_fqn

        assert _encode_fqn("O'Brien.tag") == "O''Brien.tag"


# ═══════════════════════════════════════════════════════════════════════════
#  Client Tests
# ═══════════════════════════════════════════════════════════════════════════


def _mock_settings(**overrides):
    """Create AVEVAHistorianSettings with test defaults."""
    from mes.adapters.historian.aveva.config import AVEVAHistorianSettings

    defaults = {
        "AVEVA_BASE_URL": "http://historian:32569/Historian/v2",
        "AVEVA_AUTH_MODE": "basic",
        "AVEVA_USERNAME": "testuser",
        "AVEVA_PASSWORD": "testpass",
        "AVEVA_DATASOURCE": "TestSource",
        "AVEVA_EQUIPMENT_ID": "equip-001",
    }
    defaults.update(overrides)
    return AVEVAHistorianSettings(_env_file=None, **defaults)


def _make_odata_response(values: list[dict]) -> MagicMock:
    """Create a mock httpx.Response with OData format."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"@odata.context": "...", "value": values}
    resp.raise_for_status = MagicMock()
    return resp


class TestAVEVAHistorianClient:
    """Test the HTTP client wrapping AVEVA Historian REST API."""

    @pytest.mark.asyncio
    async def test_connect_basic_auth(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings(AVEVA_AUTH_MODE="basic")
        client = AVEVAHistorianClient(settings)

        mock_async_client = AsyncMock()
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock(return_value=mock_async_client)
        mock_httpx.BasicAuth = MagicMock(return_value="basic_auth_obj")
        mock_httpx.Timeout = MagicMock(return_value="timeout_obj")

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            import importlib
            import mes.adapters.historian.aveva.client as client_mod
            importlib.reload(client_mod)

            fresh_client = client_mod.AVEVAHistorianClient(settings)
            await fresh_client.connect()

            mock_httpx.BasicAuth.assert_called_once_with("testuser", "testpass")
            mock_httpx.AsyncClient.assert_called_once()
            assert fresh_client._http is not None

        await fresh_client.disconnect()

    @pytest.mark.asyncio
    async def test_connect_bearer_auth(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings(
            AVEVA_AUTH_MODE="bearer",
            AVEVA_BEARER_TOKEN="my-token-123",
        )
        client = AVEVAHistorianClient(settings)

        mock_async_client = AsyncMock()
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock(return_value=mock_async_client)
        mock_httpx.Timeout = MagicMock(return_value="timeout_obj")

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            import importlib
            import mes.adapters.historian.aveva.client as client_mod
            importlib.reload(client_mod)

            fresh_client = client_mod.AVEVAHistorianClient(settings)
            await fresh_client.connect()

            # Bearer auth → no httpx auth object, token in headers
            call_kwargs = mock_httpx.AsyncClient.call_args[1]
            assert call_kwargs["auth"] is None
            assert call_kwargs["headers"]["Authorization"] == "Bearer my-token-123"

        await fresh_client.disconnect()

    @pytest.mark.asyncio
    async def test_connect_negotiate_with_ntlm(self):
        settings = _mock_settings(AVEVA_AUTH_MODE="negotiate")

        mock_ntlm_auth = MagicMock()
        mock_ntlm_module = MagicMock()
        mock_ntlm_module.HttpNtlmAuth = MagicMock(return_value=mock_ntlm_auth)

        mock_async_client = AsyncMock()
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock(return_value=mock_async_client)
        mock_httpx.Timeout = MagicMock(return_value="timeout_obj")

        with patch.dict("sys.modules", {
            "httpx": mock_httpx,
            "httpx_ntlm": mock_ntlm_module,
        }):
            import importlib
            import mes.adapters.historian.aveva.client as client_mod
            importlib.reload(client_mod)

            fresh_client = client_mod.AVEVAHistorianClient(settings)
            await fresh_client.connect()

            mock_ntlm_module.HttpNtlmAuth.assert_called_once_with("testuser", "testpass")
            call_kwargs = mock_httpx.AsyncClient.call_args[1]
            assert call_kwargs["auth"] is mock_ntlm_auth

        await fresh_client.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        mock_http = AsyncMock()
        client._http = mock_http

        await client.disconnect()

        mock_http.aclose.assert_awaited_once()
        assert client._http is None

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        mock_http = AsyncMock()
        mock_http.get.return_value = MagicMock(status_code=200)
        client._http = mock_http

        result = await client.health_check()

        assert result is True
        mock_http.get.assert_awaited_once_with("/Tags", params={"$top": "1"})

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        mock_http = AsyncMock()
        mock_http.get.side_effect = Exception("Connection refused")
        client._http = mock_http

        result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_not_connected(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)

        result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_tags(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        tags_data = [
            {"FQN": "TestSource.temp", "TagName": "temp", "TagType": "Analog"},
            {"FQN": "TestSource.pressure", "TagName": "pressure", "TagType": "Analog"},
        ]
        mock_http = AsyncMock()
        mock_http.get.return_value = _make_odata_response(tags_data)
        client._http = mock_http

        result = await client.get_tags(source="TestSource")

        assert len(result) == 2
        assert result[0]["FQN"] == "TestSource.temp"
        call_params = mock_http.get.call_args[1]["params"]
        assert "$filter" in call_params
        assert "TestSource" in call_params["$filter"]

    @pytest.mark.asyncio
    async def test_get_tags_with_tag_filter(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        mock_http = AsyncMock()
        mock_http.get.return_value = _make_odata_response([])
        client._http = mock_http

        await client.get_tags(tag_filter="startswith(FQN,'TestSource.Line1_')")

        call_params = mock_http.get.call_args[1]["params"]
        assert call_params["TagFilter"] == "startswith(FQN,'TestSource.Line1_')"

    @pytest.mark.asyncio
    async def test_get_process_values(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        vtq_data = [
            {
                "FQN": "TestSource.temp",
                "DateTime": "2025-06-15T12:00:00Z",
                "OpcQuality": 192,
                "Value": 72.5,
            },
            {
                "FQN": "TestSource.temp",
                "DateTime": "2025-06-15T12:01:00Z",
                "OpcQuality": 192,
                "Value": 73.1,
            },
        ]
        mock_http = AsyncMock()
        mock_http.get.return_value = _make_odata_response(vtq_data)
        client._http = mock_http

        start = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
        result = await client.get_process_values(
            "TestSource.temp", start, end, retrieval_mode="Full",
        )

        assert len(result) == 2
        assert result[0]["Value"] == 72.5
        call_params = mock_http.get.call_args[1]["params"]
        assert "FQN eq 'TestSource.temp'" in call_params["$filter"]
        assert call_params["RetrievalMode"] == "Full"

    @pytest.mark.asyncio
    async def test_get_process_values_with_resolution(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        mock_http = AsyncMock()
        mock_http.get.return_value = _make_odata_response([])
        client._http = mock_http

        start = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
        await client.get_process_values(
            "TestSource.temp", start, end,
            retrieval_mode="Average", resolution=3600000,
        )

        call_params = mock_http.get.call_args[1]["params"]
        assert call_params["Resolution"] == "3600000"
        assert call_params["RetrievalMode"] == "Average"

    @pytest.mark.asyncio
    async def test_get_current_value(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        vtq = {"FQN": "TestSource.temp", "Value": 72.5, "OpcQuality": 192}
        mock_http = AsyncMock()
        mock_http.get.return_value = _make_odata_response([vtq])
        client._http = mock_http

        result = await client.get_current_value("TestSource.temp")

        assert result is not None
        assert result["Value"] == 72.5

    @pytest.mark.asyncio
    async def test_get_current_value_not_found(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        mock_http = AsyncMock()
        mock_http.get.return_value = _make_odata_response([])
        client._http = mock_http

        result = await client.get_current_value("TestSource.nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_analog_summary(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        summary_data = [
            {
                "FQN": "TestSource.temp",
                "Average": 72.5,
                "StdDev": 1.2,
                "Minimum": 70.0,
                "Maximum": 75.0,
                "PercentGood": 99.5,
            },
        ]
        mock_http = AsyncMock()
        mock_http.get.return_value = _make_odata_response(summary_data)
        client._http = mock_http

        start = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
        result = await client.get_analog_summary(
            "TestSource.temp", start, end, resolution=3600000,
        )

        assert len(result) == 1
        assert result[0]["Average"] == 72.5
        call_params = mock_http.get.call_args[1]["params"]
        assert "FQN eq 'TestSource.temp'" in call_params["$filter"]
        assert call_params["Resolution"] == "3600000"
        assert call_params["RetrievalMode"] == "Cyclic"

    @pytest.mark.asyncio
    async def test_get_state_summary(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        state_data = [
            {"Text": "Running", "Count": 10, "Total": 3600.0, "Average": 360.0},
            {"Text": "Idle", "Count": 5, "Total": 1200.0, "Average": 240.0},
        ]
        mock_http = AsyncMock()
        mock_http.get.return_value = _make_odata_response(state_data)
        client._http = mock_http

        start = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
        result = await client.get_state_summary("TestSource.state", start, end)

        assert len(result) == 2
        assert result[0]["Text"] == "Running"
        assert result[1]["Total"] == 1200.0

    @pytest.mark.asyncio
    async def test_get_events(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        events_data = [
            {"FQN": "TestSource.alarm1", "DateTime": "2025-06-15T12:00:00Z"},
        ]
        mock_http = AsyncMock()
        mock_http.get.return_value = _make_odata_response(events_data)
        client._http = mock_http

        result = await client.get_events("TestSource.alarm1")

        assert len(result) == 1
        assert result[0]["FQN"] == "TestSource.alarm1"

    @pytest.mark.asyncio
    async def test_get_odata_not_connected(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)

        with pytest.raises(RuntimeError, match="not connected"):
            await client.get_process_values("TestSource.temp")

    @pytest.mark.asyncio
    async def test_get_process_values_by_filter(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        mock_http = AsyncMock()
        mock_http.get.return_value = _make_odata_response([
            {"FQN": "TestSource.temp1", "Value": 70.0},
            {"FQN": "TestSource.temp2", "Value": 75.0},
        ])
        client._http = mock_http

        start = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
        result = await client.get_process_values_by_filter(
            "startswith(FQN,'TestSource.temp')", start, end,
        )

        assert len(result) == 2
        call_params = mock_http.get.call_args[1]["params"]
        assert call_params["TagFilter"] == "startswith(FQN,'TestSource.temp')"

    @pytest.mark.asyncio
    async def test_search_tags(self):
        from mes.adapters.historian.aveva.client import AVEVAHistorianClient

        settings = _mock_settings()
        client = AVEVAHistorianClient(settings)
        mock_http = AsyncMock()
        mock_http.get.return_value = _make_odata_response([
            {"FQN": "TestSource.temp1", "TagName": "temp1"},
        ])
        client._http = mock_http

        result = await client.search_tags("TestSource.temp")

        assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════════════
#  Adapter Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAVEVAHistorianAdapter:
    """Test the EquipmentAdapter implementation wrapping the client."""

    def _make_adapter(self, **settings_overrides):
        from mes.adapters.historian.aveva.adapter import AVEVAHistorianAdapter

        settings = _mock_settings(**settings_overrides)
        adapter = AVEVAHistorianAdapter(settings)
        return adapter

    @pytest.mark.asyncio
    async def test_equipment_id(self):
        adapter = self._make_adapter(AVEVA_EQUIPMENT_ID="equip-abc")
        assert adapter.equipment_id == "equip-abc"

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        adapter = self._make_adapter()
        adapter._client = AsyncMock()

        await adapter.connect()

        adapter._client.connect.assert_awaited_once()
        assert adapter._poll_task is not None

        await adapter.disconnect()

        adapter._client.disconnect.assert_awaited_once()
        assert adapter._poll_task is None

    @pytest.mark.asyncio
    async def test_health_check(self):
        adapter = self._make_adapter()
        adapter._client = AsyncMock()
        adapter._client.health_check.return_value = True

        result = await adapter.health_check()

        assert result is True
        adapter._client.health_check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_read_tag_fqn(self):
        adapter = self._make_adapter(AVEVA_DATASOURCE="TestSource")
        adapter._client = AsyncMock()
        adapter._client.get_current_value.return_value = {
            "FQN": "TestSource.temp",
            "Value": 72.5,
            "OpcQuality": 192,
            "DateTime": "2025-06-15T12:00:00Z",
        }

        result = await adapter.read_tag("TestSource.temp")

        assert result.tag_name == "TestSource.temp"
        assert result.value == 72.5
        assert result.quality == "good"
        adapter._client.get_current_value.assert_awaited_once_with("TestSource.temp")

    @pytest.mark.asyncio
    async def test_read_tag_short_name_resolves_fqn(self):
        adapter = self._make_adapter(AVEVA_DATASOURCE="Baytown")
        adapter._client = AsyncMock()
        adapter._client.get_current_value.return_value = {
            "FQN": "Baytown.tank_level",
            "Value": 55.0,
            "OpcQuality": 192,
            "DateTime": "2025-06-15T12:00:00Z",
        }

        result = await adapter.read_tag("tank_level")

        # Should have been resolved to Baytown.tank_level
        adapter._client.get_current_value.assert_awaited_once_with("Baytown.tank_level")
        assert result.value == 55.0

    @pytest.mark.asyncio
    async def test_read_tag_not_found(self):
        adapter = self._make_adapter()
        adapter._client = AsyncMock()
        adapter._client.get_current_value.return_value = None

        result = await adapter.read_tag("nonexistent")

        assert result.value is None
        assert result.quality == "bad"

    @pytest.mark.asyncio
    async def test_read_tag_quality_mapping(self):
        adapter = self._make_adapter()
        adapter._client = AsyncMock()

        # Bad quality (OPC = 0)
        adapter._client.get_current_value.return_value = {
            "Value": 10.0,
            "OpcQuality": 0,
            "DateTime": "2025-06-15T12:00:00Z",
        }
        result = await adapter.read_tag("TestSource.tag")
        assert result.quality == "bad"

        # Uncertain quality (OPC = 64)
        adapter._client.get_current_value.return_value = {
            "Value": 10.0,
            "OpcQuality": 64,
            "DateTime": "2025-06-15T12:00:00Z",
        }
        result = await adapter.read_tag("TestSource.tag")
        assert result.quality == "uncertain"

    @pytest.mark.asyncio
    async def test_write_tag_raises(self):
        adapter = self._make_adapter()

        with pytest.raises(NotImplementedError, match="does not support writing"):
            await adapter.write_tag("TestSource.temp", 99.0)

    @pytest.mark.asyncio
    async def test_subscribe_tag(self):
        adapter = self._make_adapter()
        callback = AsyncMock()

        handle = await adapter.subscribe_tag("TestSource.temp", callback, 2000)

        assert handle.tag_name == "TestSource.temp"
        assert handle.active is True
        assert handle.handle_id in adapter._subscriptions

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        adapter = self._make_adapter()
        callback = AsyncMock()

        handle = await adapter.subscribe_tag("TestSource.temp", callback)
        await adapter.unsubscribe(handle)

        assert handle.active is False
        assert handle.handle_id not in adapter._subscriptions

    @pytest.mark.asyncio
    async def test_get_equipment_state_with_state_tag(self):
        adapter = self._make_adapter(
            AVEVA_STATE_TAG_FQN="TestSource.machine_state",
            AVEVA_EQUIPMENT_ID="equip-001",
        )
        adapter._client = AsyncMock()
        adapter._client.get_current_value.return_value = {
            "FQN": "TestSource.machine_state",
            "Value": 6,
            "Text": "Running",
            "OpcQuality": 192,
            "DateTime": "2025-06-15T12:00:00Z",
        }

        state = await adapter.get_equipment_state()

        assert state.equipment_id == "equip-001"
        assert state.state == "running"
        assert state.dispatch_category == "busy"
        assert state.oee_bucket == "uptime_value_add"

    @pytest.mark.asyncio
    async def test_get_equipment_state_no_tag(self):
        adapter = self._make_adapter(AVEVA_STATE_TAG_FQN="")

        state = await adapter.get_equipment_state()

        assert state.state == "unknown"

    @pytest.mark.asyncio
    async def test_get_equipment_state_tag_returns_none(self):
        adapter = self._make_adapter(AVEVA_STATE_TAG_FQN="TestSource.state")
        adapter._client = AsyncMock()
        adapter._client.get_current_value.return_value = None

        state = await adapter.get_equipment_state()

        assert state.state == "unknown"
        assert state.dispatch_category == "unavailable_unplanned"

    @pytest.mark.asyncio
    async def test_get_equipment_state_fault(self):
        adapter = self._make_adapter(
            AVEVA_STATE_TAG_FQN="TestSource.state",
        )
        adapter._client = AsyncMock()
        adapter._client.get_current_value.return_value = {
            "Value": 8,
            "Text": "Fault",
            "OpcQuality": 192,
            "DateTime": "2025-06-15T12:00:00Z",
        }

        state = await adapter.get_equipment_state()

        assert state.state == "fault"
        assert state.dispatch_category == "unavailable_unplanned"
        assert state.oee_bucket == "downtime_unplanned"

    @pytest.mark.asyncio
    async def test_browse_tags(self):
        adapter = self._make_adapter(AVEVA_DATASOURCE="TestSource")
        adapter._client = AsyncMock()
        adapter._client.get_tags.return_value = [
            {"FQN": "TestSource.temp", "TagType": "Analog", "Description": "Temp sensor"},
            {"FQN": "TestSource.valve", "TagType": "Discrete", "Description": "Valve open"},
            {"FQN": "TestSource.status", "TagType": "String", "Description": "Status msg"},
        ]

        result = await adapter.browse_tags()

        assert len(result) == 3
        assert result[0].tag_name == "TestSource.temp"
        assert result[0].data_type == "float"
        assert result[0].access == "read"
        assert result[0].description == "Temp sensor"

        assert result[1].data_type == "bool"
        assert result[2].data_type == "string"

    @pytest.mark.asyncio
    async def test_browse_tags_with_root(self):
        adapter = self._make_adapter()
        adapter._client = AsyncMock()
        adapter._client.get_tags.return_value = []

        await adapter.browse_tags(root="TestSource.Line1_")

        call_kwargs = adapter._client.get_tags.call_args[1]
        assert "startswith(FQN,'TestSource.Line1_')" in call_kwargs["tag_filter"]

    @pytest.mark.asyncio
    async def test_get_analog_summary_extended(self):
        adapter = self._make_adapter()
        adapter._client = AsyncMock()
        adapter._client.get_analog_summary.return_value = [
            {"Average": 72.5, "Minimum": 70.0, "Maximum": 75.0},
        ]

        start = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
        result = await adapter.get_analog_summary(
            "TestSource.temp", start, end, resolution_ms=3600000,
        )

        assert len(result) == 1
        assert result[0]["Average"] == 72.5

    @pytest.mark.asyncio
    async def test_get_state_summary_extended(self):
        adapter = self._make_adapter()
        adapter._client = AsyncMock()
        adapter._client.get_state_summary.return_value = [
            {"Text": "Running", "Total": 3600.0},
        ]

        start = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
        result = await adapter.get_state_summary("TestSource.state", start, end)

        assert len(result) == 1
        assert result[0]["Text"] == "Running"

    @pytest.mark.asyncio
    async def test_get_historical(self):
        adapter = self._make_adapter()
        adapter._client = AsyncMock()
        adapter._client.get_process_values.return_value = [
            {
                "FQN": "TestSource.temp",
                "Value": 72.5,
                "OpcQuality": 192,
                "DateTime": "2025-06-15T12:00:00Z",
            },
            {
                "FQN": "TestSource.temp",
                "Value": 73.1,
                "OpcQuality": 192,
                "DateTime": "2025-06-15T12:01:00Z",
            },
        ]

        start = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 6, 15, 13, 0, 0, tzinfo=timezone.utc)
        result = await adapter.get_historical(
            "TestSource.temp", start, end, retrieval_mode="Full",
        )

        assert len(result) == 2
        assert result[0].tag_name == "TestSource.temp"
        assert result[0].value == 72.5
        assert result[0].quality == "good"

    @pytest.mark.asyncio
    async def test_vtq_to_tag_value_data_types(self):
        """Test data type inference from VTQ records."""
        from mes.adapters.historian.aveva.adapter import AVEVAHistorianAdapter

        # Float
        tv = AVEVAHistorianAdapter._vtq_to_tag_value(
            "t", {"Value": 1.5, "OpcQuality": 192, "DateTime": "2025-01-01T00:00:00Z"},
        )
        assert tv.data_type == "float"

        # Integer
        tv = AVEVAHistorianAdapter._vtq_to_tag_value(
            "t", {"Value": 42, "OpcQuality": 192, "DateTime": "2025-01-01T00:00:00Z"},
        )
        assert tv.data_type == "int"

        # Boolean
        tv = AVEVAHistorianAdapter._vtq_to_tag_value(
            "t", {"Value": True, "OpcQuality": 192, "DateTime": "2025-01-01T00:00:00Z"},
        )
        assert tv.data_type == "bool"

        # String from Text field
        tv = AVEVAHistorianAdapter._vtq_to_tag_value(
            "t", {"Value": None, "Text": "Running", "OpcQuality": 192, "DateTime": "2025-01-01T00:00:00Z"},
        )
        assert tv.data_type == "string"
        assert tv.value == "Running"

    @pytest.mark.asyncio
    async def test_resolve_fqn(self):
        adapter = self._make_adapter(AVEVA_DATASOURCE="Baytown")

        # Already FQN (has dot)
        assert adapter._resolve_fqn("Baytown.temp") == "Baytown.temp"

        # Short name → prepend datasource
        assert adapter._resolve_fqn("temp") == "Baytown.temp"

    @pytest.mark.asyncio
    async def test_resolve_fqn_no_datasource(self):
        adapter = self._make_adapter(AVEVA_DATASOURCE="")
        assert adapter._resolve_fqn("temp") == "temp"


# ═══════════════════════════════════════════════════════════════════════════
#  Poll Loop Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPollLoop:
    """Test the background polling subscription mechanism."""

    @pytest.mark.asyncio
    async def test_poll_invokes_callback_on_change(self):
        """Verify polling detects a value change and calls the callback."""
        from mes.adapters.historian.aveva.adapter import AVEVAHistorianAdapter

        settings = _mock_settings()
        adapter = AVEVAHistorianAdapter(settings)
        adapter._client = AsyncMock()

        # First poll returns value 72.5, second returns 73.0
        adapter._client.get_current_value.side_effect = [
            {"FQN": "TestSource.temp", "Value": 72.5, "OpcQuality": 192, "DateTime": "2025-06-15T12:00:00Z"},
            {"FQN": "TestSource.temp", "Value": 73.0, "OpcQuality": 192, "DateTime": "2025-06-15T12:01:00Z"},
        ]

        callback = AsyncMock()
        handle = await adapter.subscribe_tag("TestSource.temp", callback, interval_ms=100)

        # Start the poll loop
        adapter._poll_task = asyncio.create_task(adapter._poll_loop())

        # Allow a few poll cycles
        await asyncio.sleep(0.5)

        # Stop polling
        adapter._poll_task.cancel()
        try:
            await adapter._poll_task
        except asyncio.CancelledError:
            pass

        # Callback should have been invoked (at least once for first change from None→72.5)
        assert callback.call_count >= 1
        first_call_value = callback.call_args_list[0][0][0]
        assert first_call_value.tag_name == "TestSource.temp"

    @pytest.mark.asyncio
    async def test_poll_skips_unchanged_values(self):
        """Verify polling does not invoke callback when value unchanged."""
        from mes.adapters.historian.aveva.adapter import AVEVAHistorianAdapter

        settings = _mock_settings()
        adapter = AVEVAHistorianAdapter(settings)
        adapter._client = AsyncMock()

        # Same value returned every time
        adapter._client.get_current_value.return_value = {
            "FQN": "TestSource.temp",
            "Value": 72.5,
            "OpcQuality": 192,
            "DateTime": "2025-06-15T12:00:00Z",
        }

        callback = AsyncMock()
        await adapter.subscribe_tag("TestSource.temp", callback, interval_ms=100)

        adapter._poll_task = asyncio.create_task(adapter._poll_loop())
        await asyncio.sleep(0.5)

        adapter._poll_task.cancel()
        try:
            await adapter._poll_task
        except asyncio.CancelledError:
            pass

        # Only called once for the initial value (None→72.5), not for subsequent same-value reads
        assert callback.call_count == 1


# ═══════════════════════════════════════════════════════════════════════════
#  Plugin Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAVEVAHistorianPlugin:
    """Test the plugin wrapper for lifecycle and config mapping."""

    @pytest.mark.asyncio
    async def test_initialize_creates_adapter(self):
        from plugins.system.aveva_historian.plugin import AVEVAHistorianPlugin

        plugin = AVEVAHistorianPlugin()
        config = {
            "base_url": "http://historian:32569/Historian/v2",
            "datasource": "TestSource",
            "equipment_id": "equip-001",
            "auth_mode": "basic",
            "username": "user",
            "password": "pass",
        }

        await plugin.initialize(config)

        assert plugin._adapter is not None
        assert plugin._adapter.equipment_id == "equip-001"

    @pytest.mark.asyncio
    async def test_start_connects_adapter(self):
        from plugins.system.aveva_historian.plugin import AVEVAHistorianPlugin

        plugin = AVEVAHistorianPlugin()
        plugin._adapter = AsyncMock()
        plugin._config = {"equipment_id": "equip-001"}

        await plugin.start()

        plugin._adapter.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_subscribes_to_state_tag(self):
        from plugins.system.aveva_historian.plugin import AVEVAHistorianPlugin

        plugin = AVEVAHistorianPlugin()
        plugin._adapter = AsyncMock()
        plugin._config = {
            "state_tag_fqn": "TestSource.state",
            "state_model_id": "packml",
            "equipment_id": "equip-001",
            "poll_interval_sec": 5,
        }

        await plugin.start()

        plugin._adapter.subscribe_tag.assert_awaited_once()
        call_args = plugin._adapter.subscribe_tag.call_args
        assert call_args[0][0] == "TestSource.state"
        assert call_args[1]["interval_ms"] == 5000

    @pytest.mark.asyncio
    async def test_stop_disconnects(self):
        from plugins.system.aveva_historian.plugin import AVEVAHistorianPlugin

        plugin = AVEVAHistorianPlugin()
        plugin._adapter = AsyncMock()
        mock_handle = MagicMock()
        plugin._subscription_handle = mock_handle

        await plugin.stop()

        plugin._adapter.unsubscribe.assert_awaited_once_with(mock_handle)
        plugin._adapter.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_health_check(self):
        from plugins.system.aveva_historian.plugin import AVEVAHistorianPlugin

        plugin = AVEVAHistorianPlugin()
        plugin._adapter = AsyncMock()
        plugin._adapter.health_check.return_value = True

        result = await plugin.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_no_adapter(self):
        from plugins.system.aveva_historian.plugin import AVEVAHistorianPlugin

        plugin = AVEVAHistorianPlugin()

        result = await plugin.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_adapter(self):
        from plugins.system.aveva_historian.plugin import AVEVAHistorianPlugin

        plugin = AVEVAHistorianPlugin()
        plugin._adapter = "mock_adapter"

        assert plugin.get_adapter() == "mock_adapter"


# ═══════════════════════════════════════════════════════════════════════════
#  Manifest Validation
# ═══════════════════════════════════════════════════════════════════════════


class TestManifest:
    """Validate the plugin manifest.yaml."""

    def test_manifest_loads_and_has_required_fields(self):
        import pathlib

        manifest_path = (
            pathlib.Path(__file__).resolve().parents[2]
            / "plugins"
            / "system"
            / "aveva_historian"
            / "manifest.yaml"
        )
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        assert manifest["id"] == "aveva-historian"
        assert manifest["category"] == "equipment"
        assert manifest["origin"] == "system"
        assert manifest["version"] == "1.0.0"

    def test_manifest_has_required_parameters(self):
        import pathlib

        manifest_path = (
            pathlib.Path(__file__).resolve().parents[2]
            / "plugins"
            / "system"
            / "aveva_historian"
            / "manifest.yaml"
        )
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        param_names = [p["name"] for p in manifest["parameters"]]
        assert "base_url" in param_names
        assert "datasource" in param_names
        assert "equipment_id" in param_names
        assert "auth_mode" in param_names
        assert "state_tag_fqn" in param_names

        # Check required flags
        required_params = {p["name"] for p in manifest["parameters"] if p.get("required")}
        assert "base_url" in required_params
        assert "datasource" in required_params
        assert "equipment_id" in required_params

    def test_manifest_extension_point(self):
        import pathlib

        manifest_path = (
            pathlib.Path(__file__).resolve().parents[2]
            / "plugins"
            / "system"
            / "aveva_historian"
            / "manifest.yaml"
        )
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        ext_points = manifest["extension_points"]
        assert len(ext_points) == 1
        assert ext_points[0]["type"] == "equipment_driver"
        assert ext_points[0]["name"] == "aveva_historian"
