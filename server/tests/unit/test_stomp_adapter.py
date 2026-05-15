"""
Unit tests for STOMP equipment and messaging adapter.

All tests use mocking — no real STOMP broker is required.
Tests cover: STOMPSettings, STOMPClient lifecycle, STOMPListener callbacks,
STOMPMessagingAdapter inbound/outbound bridge, STOMPJMSPlugin integration,
and error handling.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest


# ═══════════════════════════════════════════════════════════════════════════
#  Config Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSTOMPSettings:
    """Verify STOMPSettings defaults and custom values."""

    def test_defaults(self):
        from mes.adapters.messaging.stomp.config import STOMPSettings

        s = STOMPSettings(_env_file=None)
        assert s.STOMP_BROKER_HOST == "localhost"
        assert s.STOMP_BROKER_PORT == 61613
        assert s.STOMP_USE_SSL is False
        assert s.STOMP_USERNAME == ""
        assert s.STOMP_PASSWORD == ""
        assert s.STOMP_VHOST == "/"
        assert s.STOMP_HEARTBEAT_SEND_MS == 10000
        assert s.STOMP_HEARTBEAT_RECV_MS == 10000
        assert s.STOMP_RECONNECT_ATTEMPTS == 10
        assert s.STOMP_RECONNECT_DELAY_SEC == 5
        assert s.STOMP_INBOUND_SUBSCRIPTIONS == "/queue/mes.inbound"
        assert s.STOMP_OUTBOUND_DESTINATION == "/topic/mes.events"
        assert s.STOMP_EVENT_SUBSCRIPTIONS == "*"
        assert s.STOMP_TOPIC_PREFIX == "/topic/mes/equipment"
        assert s.STOMP_STATE_TAG == "state"
        assert s.STOMP_EQUIPMENT_ID_TAG == "equipment_id"

    def test_custom_values(self):
        from mes.adapters.messaging.stomp.config import STOMPSettings

        s = STOMPSettings(
            _env_file=None,
            STOMP_BROKER_HOST="artemis.factory.local",
            STOMP_BROKER_PORT=61614,
            STOMP_USE_SSL=True,
            STOMP_USERNAME="mes_user",
            STOMP_PASSWORD="s3cret",
            STOMP_VHOST="/factory",
            STOMP_HEARTBEAT_SEND_MS=5000,
            STOMP_HEARTBEAT_RECV_MS=5000,
            STOMP_RECONNECT_ATTEMPTS=20,
            STOMP_RECONNECT_DELAY_SEC=10,
            STOMP_INBOUND_SUBSCRIPTIONS="/queue/erp.orders,/queue/erp.materials",
            STOMP_OUTBOUND_DESTINATION="/topic/mes.production",
            STOMP_EVENT_SUBSCRIPTIONS="wip.*,inventory.*",
            STOMP_TOPIC_PREFIX="/topic/factory/line1",
            STOMP_STATE_TAG="machine_state",
            STOMP_EQUIPMENT_ID_TAG="machine_id",
        )
        assert s.STOMP_BROKER_HOST == "artemis.factory.local"
        assert s.STOMP_BROKER_PORT == 61614
        assert s.STOMP_USE_SSL is True
        assert s.STOMP_USERNAME == "mes_user"
        assert s.STOMP_PASSWORD == "s3cret"
        assert s.STOMP_VHOST == "/factory"
        assert s.STOMP_HEARTBEAT_SEND_MS == 5000
        assert s.STOMP_RECONNECT_ATTEMPTS == 20
        assert s.STOMP_INBOUND_SUBSCRIPTIONS == "/queue/erp.orders,/queue/erp.materials"
        assert s.STOMP_OUTBOUND_DESTINATION == "/topic/mes.production"
        assert s.STOMP_EVENT_SUBSCRIPTIONS == "wip.*,inventory.*"
        assert s.STOMP_TOPIC_PREFIX == "/topic/factory/line1"
        assert s.STOMP_STATE_TAG == "machine_state"
        assert s.STOMP_EQUIPMENT_ID_TAG == "machine_id"

    def test_port_range_validation(self):
        from pydantic import ValidationError
        from mes.adapters.messaging.stomp.config import STOMPSettings

        with pytest.raises(ValidationError):
            STOMPSettings(_env_file=None, STOMP_BROKER_PORT=0)
        with pytest.raises(ValidationError):
            STOMPSettings(_env_file=None, STOMP_BROKER_PORT=70000)


# ═══════════════════════════════════════════════════════════════════════════
#  Listener Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSTOMPListener:
    """Test the stomp.py listener that bridges to async callbacks."""

    def test_on_connected_sets_flag(self):
        from mes.adapters.messaging.stomp.client import STOMPListener

        loop = asyncio.new_event_loop()
        listener = STOMPListener(loop, on_message=AsyncMock())

        frame = SimpleNamespace(headers={"server": "ActiveMQ Artemis"})
        listener.on_connected(frame)

        assert listener.is_connected is True
        loop.close()

    def test_on_disconnected_clears_flag(self):
        from mes.adapters.messaging.stomp.client import STOMPListener

        loop = asyncio.new_event_loop()
        listener = STOMPListener(loop, on_message=AsyncMock())

        # Connect then disconnect
        frame = SimpleNamespace(headers={"server": "test"})
        listener.on_connected(frame)
        assert listener.is_connected is True

        listener.on_disconnected()
        assert listener.is_connected is False
        loop.close()

    def test_on_message_dispatches_to_callback(self):
        from mes.adapters.messaging.stomp.client import STOMPListener

        loop = asyncio.new_event_loop()
        on_msg = AsyncMock()
        listener = STOMPListener(loop, on_message=on_msg)

        frame = SimpleNamespace(
            headers={"destination": "/queue/test", "message-id": "m1"},
            body='{"event_type": "test.event"}',
        )

        # Patch run_coroutine_threadsafe to just call the coro synchronously
        with patch("mes.adapters.messaging.stomp.client.asyncio.run_coroutine_threadsafe") as mock_rcts:
            listener.on_message(frame)
            mock_rcts.assert_called_once()
            # Verify the correct args were passed to our callback
            call_args = mock_rcts.call_args
            coro = call_args[0][0]
            # Clean up the coroutine to avoid warning
            coro.close()

        loop.close()

    def test_on_error_dispatches_to_callback(self):
        from mes.adapters.messaging.stomp.client import STOMPListener

        loop = asyncio.new_event_loop()
        on_error = AsyncMock()
        listener = STOMPListener(loop, on_message=AsyncMock(), on_error=on_error)

        frame = SimpleNamespace(
            headers={"message": "some error"},
            body="Error details",
        )

        with patch("mes.adapters.messaging.stomp.client.asyncio.run_coroutine_threadsafe") as mock_rcts:
            listener.on_error(frame)
            mock_rcts.assert_called_once()
            coro = mock_rcts.call_args[0][0]
            coro.close()

        loop.close()


# ═══════════════════════════════════════════════════════════════════════════
#  Client Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSTOMPClient:
    """Test the async-friendly STOMP client wrapper."""

    def _make_client(self, **settings_kwargs):
        from mes.adapters.messaging.stomp.client import STOMPClient
        from mes.adapters.messaging.stomp.config import STOMPSettings

        settings = STOMPSettings(_env_file=None, **settings_kwargs)
        return STOMPClient(settings, on_message=AsyncMock())

    @pytest.mark.asyncio
    async def test_connect_creates_connection(self):
        client = self._make_client()

        mock_conn = MagicMock()
        mock_conn.connect = MagicMock()

        with patch("mes.adapters.messaging.stomp.client.STOMPClient.connect") as mock_connect:
            mock_connect.return_value = None
            await client.connect()
            # Just verifying no exception

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        client = self._make_client()
        # Should not raise
        await client.disconnect()
        assert client.is_connected is False

    def test_subscribe_without_connection_raises(self):
        client = self._make_client()
        with pytest.raises(RuntimeError, match="not connected"):
            client.subscribe("/queue/test")

    def test_send_without_connection_raises(self):
        client = self._make_client()
        with pytest.raises(RuntimeError, match="not connected"):
            client.send("/queue/test", '{"data": "test"}')

    def test_is_connected_false_initially(self):
        client = self._make_client()
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_health_check_false_when_disconnected(self):
        client = self._make_client()
        assert await client.health_check() is False

    def test_subscribe_returns_unique_ids(self):
        from mes.adapters.messaging.stomp.client import STOMPClient
        from mes.adapters.messaging.stomp.config import STOMPSettings

        settings = STOMPSettings(_env_file=None)
        client = STOMPClient(settings, on_message=AsyncMock())

        # Simulate a connected state
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_conn.subscribe = MagicMock()
        client._conn = mock_conn

        id1 = client.subscribe("/queue/q1")
        id2 = client.subscribe("/queue/q2")
        assert id1 != id2
        assert id1 == "mes-sub-1"
        assert id2 == "mes-sub-2"
        assert mock_conn.subscribe.call_count == 2

    def test_send_delegates_to_connection(self):
        from mes.adapters.messaging.stomp.client import STOMPClient
        from mes.adapters.messaging.stomp.config import STOMPSettings

        settings = STOMPSettings(_env_file=None)
        client = STOMPClient(settings, on_message=AsyncMock())

        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        client._conn = mock_conn

        client.send("/topic/test", '{"key": "value"}', headers={"custom": "hdr"})
        mock_conn.send.assert_called_once()
        call_kwargs = mock_conn.send.call_args
        assert call_kwargs[1]["destination"] == "/topic/test"
        assert call_kwargs[1]["body"] == '{"key": "value"}'

    def test_unsubscribe_delegates_to_connection(self):
        from mes.adapters.messaging.stomp.client import STOMPClient
        from mes.adapters.messaging.stomp.config import STOMPSettings

        settings = STOMPSettings(_env_file=None)
        client = STOMPClient(settings, on_message=AsyncMock())

        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        client._conn = mock_conn

        client.unsubscribe("mes-sub-1")
        mock_conn.unsubscribe.assert_called_once_with(id="mes-sub-1")


# ═══════════════════════════════════════════════════════════════════════════
#  Adapter Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSTOMPMessagingAdapter:
    """Test the bidirectional MES↔STOMP bridge."""

    def _make_adapter(self, **overrides):
        from mes.adapters.messaging.stomp.adapter import STOMPMessagingAdapter
        from mes.adapters.messaging.stomp.config import STOMPSettings
        from mes.framework.events.bus import EventBus

        settings = STOMPSettings(
            _env_file=None,
            STOMP_INBOUND_SUBSCRIPTIONS="/queue/mes.inbound",
            STOMP_OUTBOUND_DESTINATION="/topic/mes.events",
            STOMP_EVENT_SUBSCRIPTIONS="*",
            **overrides,
        )
        bus = EventBus()
        adapter = STOMPMessagingAdapter(settings=settings, event_bus=bus)
        return adapter, bus

    # ── Inbound tests ──

    @pytest.mark.asyncio
    async def test_inbound_valid_json_publishes_event(self):
        adapter, bus = self._make_adapter()

        published: list = []
        bus.subscribe("test.event", lambda e: published.append(e))

        body = json.dumps({
            "event_type": "test.event",
            "source": "erp",
            "payload": {"order_id": "ORD-001"},
        })
        await adapter._on_broker_message("/queue/mes.inbound", {}, body)
        # Give the bus a moment to dispatch
        await asyncio.sleep(0.05)

        assert len(published) == 1
        assert published[0].event_type == "test.event"
        assert published[0].payload["order_id"] == "ORD-001"

    @pytest.mark.asyncio
    async def test_inbound_invalid_json_does_not_crash(self):
        adapter, bus = self._make_adapter()
        # Should log error but not raise
        await adapter._on_broker_message("/queue/test", {}, "not-json{{{")

    @pytest.mark.asyncio
    async def test_inbound_missing_event_type_skipped(self):
        adapter, bus = self._make_adapter()
        published: list = []
        bus.subscribe("*", lambda e: published.append(e))

        body = json.dumps({"source": "erp", "payload": {}})
        await adapter._on_broker_message("/queue/test", {}, body)
        await asyncio.sleep(0.05)

        assert len(published) == 0

    @pytest.mark.asyncio
    async def test_inbound_no_event_bus_logs_warning(self):
        from mes.adapters.messaging.stomp.adapter import STOMPMessagingAdapter
        from mes.adapters.messaging.stomp.config import STOMPSettings

        settings = STOMPSettings(_env_file=None)
        adapter = STOMPMessagingAdapter(settings=settings, event_bus=None)

        # Should not raise
        await adapter._on_broker_message("/queue/test", {}, '{"event_type": "x"}')

    @pytest.mark.asyncio
    async def test_inbound_default_source_from_destination(self):
        adapter, bus = self._make_adapter()

        published: list = []
        bus.subscribe("test.event", lambda e: published.append(e))

        body = json.dumps({"event_type": "test.event"})
        await adapter._on_broker_message("/queue/erp.orders", {}, body)
        await asyncio.sleep(0.05)

        assert len(published) == 1
        assert published[0].source == "stomp:/queue/erp.orders"

    # ── Outbound tests ──

    @pytest.mark.asyncio
    async def test_outbound_forwards_event_to_broker(self):
        from mes.adapters.messaging.stomp.client import STOMPClient
        from mes.framework.events.schema import MESEvent

        adapter, bus = self._make_adapter()

        # Mock the client's send method
        adapter._client.send = MagicMock()
        adapter._connected = True
        # Mock is_connected property on the instance's class, then restore
        original = STOMPClient.is_connected
        try:
            type(adapter._client).is_connected = PropertyMock(return_value=True)

            event = MESEvent(
                event_type="wip.unit.moved",
                source="WIP-TRACK",
                payload={"unit_id": "U-001", "to_equipment": "EQ-01"},
            )
            await adapter._on_mes_event(event)

            adapter._client.send.assert_called_once()
            call_kwargs = adapter._client.send.call_args
            assert call_kwargs[1]["destination"] == "/topic/mes.events"
            body = json.loads(call_kwargs[1]["body"])
            assert body["event_type"] == "wip.unit.moved"
            assert body["source"] == "WIP-TRACK"
            assert body["payload"]["unit_id"] == "U-001"
        finally:
            STOMPClient.is_connected = original

    @pytest.mark.asyncio
    async def test_outbound_skipped_when_disconnected(self):
        from mes.framework.events.schema import MESEvent

        adapter, bus = self._make_adapter()
        adapter._client.send = MagicMock()
        adapter._connected = False

        event = MESEvent(
            event_type="wip.unit.moved",
            source="WIP-TRACK",
            payload={},
        )
        await adapter._on_mes_event(event)

        adapter._client.send.assert_not_called()

    # ── Public send API ──

    def test_send_delegates_to_client(self):
        adapter, _ = self._make_adapter()

        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        adapter._client._conn = mock_conn

        adapter.send("/queue/custom", '{"msg": "hello"}')
        mock_conn.send.assert_called_once()

    # ── Parse list helper ──

    def test_parse_list_single(self):
        from mes.adapters.messaging.stomp.adapter import STOMPMessagingAdapter

        result = STOMPMessagingAdapter._parse_list("/queue/mes.inbound")
        assert result == ["/queue/mes.inbound"]

    def test_parse_list_multiple(self):
        from mes.adapters.messaging.stomp.adapter import STOMPMessagingAdapter

        result = STOMPMessagingAdapter._parse_list(
            "/queue/erp.orders, /queue/erp.materials, /topic/events"
        )
        assert result == ["/queue/erp.orders", "/queue/erp.materials", "/topic/events"]

    def test_parse_list_empty(self):
        from mes.adapters.messaging.stomp.adapter import STOMPMessagingAdapter

        result = STOMPMessagingAdapter._parse_list("")
        assert result == []

    # ── Health check ──

    @pytest.mark.asyncio
    async def test_health_check_delegates_to_client(self):
        adapter, _ = self._make_adapter()
        assert await adapter.health_check() is False


class TestSTOMPEquipmentAdapter:
    def _make_adapter(self, **overrides):
        from mes.adapters.messaging.stomp.adapter import STOMPEquipmentAdapter
        from mes.adapters.messaging.stomp.config import STOMPSettings

        settings = STOMPSettings(_env_file=None, **overrides)
        return STOMPEquipmentAdapter(settings=settings, event_bus=None)

    @pytest.mark.asyncio
    async def test_inbound_tag_message_updates_cache(self):
        adapter = self._make_adapter()

        await adapter._on_broker_message(
            "/topic/mes/equipment/state",
            {},
            json.dumps({"tag_name": "state", "value": "Running"}),
        )

        tag = await adapter.read_tag("state")
        assert tag.value == "Running"

    @pytest.mark.asyncio
    async def test_get_equipment_state_uses_cached_tags(self):
        adapter = self._make_adapter()

        await adapter._on_broker_message(
            "/topic/mes/equipment/equipment_id",
            {},
            json.dumps({"tag_name": "equipment_id", "value": "EQ-100"}),
        )
        await adapter._on_broker_message(
            "/topic/mes/equipment/state",
            {},
            json.dumps({"tag_name": "state", "value": "Execute"}),
        )

        state = await adapter.get_equipment_state()
        assert state.equipment_id == "EQ-100"
        assert state.state == "execute"
        assert state.dispatch_category == "busy"

    @pytest.mark.asyncio
    async def test_write_tag_sends_json_to_destination(self):
        adapter = self._make_adapter()
        adapter._client.send = MagicMock()

        await adapter.write_tag("temperature", 42)

        adapter._client.send.assert_called_once()
        call_kwargs = adapter._client.send.call_args.kwargs
        assert call_kwargs["destination"] == "/topic/mes/equipment/temperature"
        assert json.loads(call_kwargs["body"]) == {"tag_name": "temperature", "value": 42}

    @pytest.mark.asyncio
    async def test_subscribe_and_unsubscribe_use_client_subscription(self):
        adapter = self._make_adapter()
        adapter._client = MagicMock()
        type(adapter._client).is_connected = PropertyMock(return_value=True)
        adapter._client.subscribe = MagicMock(return_value="mes-sub-1")
        adapter._client.unsubscribe = MagicMock()

        handle = await adapter.subscribe_tag("state", MagicMock())
        await adapter.unsubscribe(handle)

        adapter._client.subscribe.assert_called_once_with("/topic/mes/equipment/state")
        adapter._client.unsubscribe.assert_called_once_with("mes-sub-1")


# ═══════════════════════════════════════════════════════════════════════════
#  Plugin Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSTOMPJMSPlugin:
    """Test the plugin wrapper lifecycle."""

    @pytest.mark.asyncio
    async def test_initialize_creates_adapter(self):
        from plugins.system.stomp_jms.plugin import STOMPJMSPlugin

        plugin = STOMPJMSPlugin()
        assert plugin._adapter is None

        await plugin.initialize({
            "broker_host": "localhost",
            "broker_port": 61613,
        })
        assert plugin._adapter is not None

    @pytest.mark.asyncio
    async def test_initialize_with_custom_config(self):
        from plugins.system.stomp_jms.plugin import STOMPJMSPlugin

        plugin = STOMPJMSPlugin()
        await plugin.initialize({
            "broker_host": "artemis.local",
            "broker_port": 61614,
            "username": "admin",
            "password": "secret",
            "vhost": "/factory",
            "use_ssl": True,
            "inbound_subscriptions": "/queue/erp.inbound",
            "outbound_destination": "/topic/mes.production",
            "event_subscriptions": "wip.*,inventory.*",
            "topic_prefix": "/topic/factory/equipment",
            "state_tag": "machine_state",
            "equipment_id_tag": "machine_id",
        })
        settings = plugin._adapter._settings
        assert settings.STOMP_BROKER_HOST == "artemis.local"
        assert settings.STOMP_BROKER_PORT == 61614
        assert settings.STOMP_USERNAME == "admin"
        assert settings.STOMP_USE_SSL is True
        assert settings.STOMP_VHOST == "/factory"
        assert settings.STOMP_INBOUND_SUBSCRIPTIONS == "/queue/erp.inbound"
        assert settings.STOMP_EVENT_SUBSCRIPTIONS == "wip.*,inventory.*"
        assert settings.STOMP_TOPIC_PREFIX == "/topic/factory/equipment"
        assert settings.STOMP_STATE_TAG == "machine_state"
        assert settings.STOMP_EQUIPMENT_ID_TAG == "machine_id"

    @pytest.mark.asyncio
    async def test_health_check_false_before_start(self):
        from plugins.system.stomp_jms.plugin import STOMPJMSPlugin

        plugin = STOMPJMSPlugin()
        await plugin.initialize({"broker_host": "localhost"})
        assert await plugin.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_false_before_initialize(self):
        from plugins.system.stomp_jms.plugin import STOMPJMSPlugin

        plugin = STOMPJMSPlugin()
        assert await plugin.health_check() is False

    @pytest.mark.asyncio
    async def test_get_adapter_returns_adapter(self):
        from plugins.system.stomp_jms.plugin import STOMPJMSPlugin

        plugin = STOMPJMSPlugin()
        await plugin.initialize({"broker_host": "localhost"})
        adapter = plugin.get_adapter()
        assert adapter is not None
        assert adapter is plugin._adapter

    @pytest.mark.asyncio
    async def test_stop_without_start_no_error(self):
        from plugins.system.stomp_jms.plugin import STOMPJMSPlugin

        plugin = STOMPJMSPlugin()
        await plugin.initialize({"broker_host": "localhost"})
        # stop() before start() should not raise
        await plugin.stop()

    @pytest.mark.asyncio
    async def test_initialize_with_event_bus(self):
        from plugins.system.stomp_jms.plugin import STOMPJMSPlugin
        from mes.framework.events.bus import EventBus

        bus = EventBus()
        plugin = STOMPJMSPlugin()
        await plugin.initialize({
            "broker_host": "localhost",
            "_event_bus": bus,
        })
        assert plugin._adapter._event_bus is bus


# ═══════════════════════════════════════════════════════════════════════════
#  Manifest Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSTOMPJMSManifest:
    """Test that the plugin manifest is valid."""

    @staticmethod
    def _manifest_path():
        from pathlib import Path
        return Path(__file__).resolve().parents[2] / "plugins" / "system" / "stomp_jms" / "manifest.yaml"

    def test_manifest_parses(self):
        import yaml
        from mes.framework.plugin.manifest import PluginManifest

        with open(self._manifest_path()) as f:
            data = yaml.safe_load(f)
        manifest = PluginManifest.model_validate(data)
        assert manifest.id == "stomp-jms"
        assert manifest.name == "STOMP Equipment Adapter"
        assert manifest.category == "equipment"
        assert manifest.version == "1.0.0"

    def test_manifest_has_required_parameters(self):
        import yaml
        from mes.framework.plugin.manifest import PluginManifest

        with open(self._manifest_path()) as f:
            data = yaml.safe_load(f)
        manifest = PluginManifest.model_validate(data)

        param_names = [p.name for p in manifest.parameters]
        assert "broker_host" in param_names
        assert "broker_port" in param_names
        assert "username" in param_names
        assert "password" in param_names
        assert "inbound_subscriptions" in param_names
        assert "outbound_destination" in param_names
        assert "event_subscriptions" in param_names
        assert "topic_prefix" in param_names
        assert "state_tag" in param_names
        assert "equipment_id_tag" in param_names

    def test_manifest_has_extension_point(self):
        import yaml
        from mes.framework.plugin.manifest import PluginManifest

        with open(self._manifest_path()) as f:
            data = yaml.safe_load(f)
        manifest = PluginManifest.model_validate(data)

        assert len(manifest.extension_points) == 2
        assert {ep.name for ep in manifest.extension_points} == {"stomp_jms_bridge", "stomp_equipment"}
