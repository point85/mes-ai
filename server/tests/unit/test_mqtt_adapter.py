"""
Unit tests for MQTT Equipment Adapter.

All tests use mocking — no real MQTT broker is required.
Tests cover: MQTTSettings, MQTTClient lifecycle, tag operations,
payload encoding/decoding, MQTTEquipmentAdapter, state mapping,
and adapter plugin integration.
"""

from __future__ import annotations

import asyncio
import json
import ssl
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from mes.adapters.equipment.dtos import (
    EquipmentState,
    SubscriptionHandle,
    TagInfo,
    TagValue,
)
from mes.adapters.equipment.exceptions import (
    CommunicationTimeoutError,
    EquipmentConnectionError,
    TagNotFoundError,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Config Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestMQTTSettings:
    """Verify MQTTSettings defaults and custom values."""

    def test_defaults(self):
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        s = MQTTSettings(
            _env_file=None,
            EQUIP_MQTT_BROKER_HOST="localhost",
        )
        assert s.EQUIP_MQTT_BROKER_HOST == "localhost"
        assert s.EQUIP_MQTT_BROKER_PORT == 1883
        assert s.EQUIP_MQTT_USE_TLS is False
        assert s.EQUIP_MQTT_QOS == 1
        assert s.EQUIP_MQTT_KEEPALIVE == 60
        assert s.EQUIP_MQTT_TOPIC_PREFIX == "mes/equipment"
        assert s.EQUIP_MQTT_EQUIPMENT_ID == "MQTT-EQUIP-01"
        assert s.EQUIP_MQTT_CLIENT_ID == "mes-mqtt-equip-01"
        assert s.EQUIP_MQTT_TIMEOUT == 10

    def test_custom_values(self):
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        s = MQTTSettings(
            _env_file=None,
            EQUIP_MQTT_BROKER_HOST="mqtt.factory.local",
            EQUIP_MQTT_BROKER_PORT=8883,
            EQUIP_MQTT_USE_TLS=True,
            EQUIP_MQTT_USERNAME="operator",
            EQUIP_MQTT_PASSWORD="secret",
            EQUIP_MQTT_QOS=2,
            EQUIP_MQTT_TOPIC_PREFIX="factory/line1",
            EQUIP_MQTT_EQUIPMENT_ID="LINE1-EQUIP-01",
            EQUIP_MQTT_STATE_TOPIC="factory/line1/state",
        )
        assert s.EQUIP_MQTT_BROKER_HOST == "mqtt.factory.local"
        assert s.EQUIP_MQTT_BROKER_PORT == 8883
        assert s.EQUIP_MQTT_USE_TLS is True
        assert s.EQUIP_MQTT_USERNAME == "operator"
        assert s.EQUIP_MQTT_QOS == 2
        assert s.EQUIP_MQTT_TOPIC_PREFIX == "factory/line1"
        assert s.EQUIP_MQTT_EQUIPMENT_ID == "LINE1-EQUIP-01"
        assert s.EQUIP_MQTT_STATE_TOPIC == "factory/line1/state"


# ═══════════════════════════════════════════════════════════════════════════
#  Helper Function Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestHelperFunctions:
    """Test _infer_python_type, _encode_payload, _decode_payload."""

    def test_infer_bool(self):
        from mes.adapters.equipment.mqtt.client import _infer_python_type

        assert _infer_python_type(True) == "bool"
        assert _infer_python_type(False) == "bool"

    def test_infer_int(self):
        from mes.adapters.equipment.mqtt.client import _infer_python_type

        assert _infer_python_type(42) == "int"

    def test_infer_float(self):
        from mes.adapters.equipment.mqtt.client import _infer_python_type

        assert _infer_python_type(3.14) == "float"

    def test_infer_list(self):
        from mes.adapters.equipment.mqtt.client import _infer_python_type

        assert _infer_python_type([1, 2, 3]) == "array"

    def test_infer_dict(self):
        from mes.adapters.equipment.mqtt.client import _infer_python_type

        assert _infer_python_type({"a": 1}) == "object"

    def test_infer_string(self):
        from mes.adapters.equipment.mqtt.client import _infer_python_type

        assert _infer_python_type("hello") == "string"
        assert _infer_python_type(None) == "string"

    def test_encode_bytes_passthrough(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient

        assert MQTTClient._encode_payload(b"\x01\x02") == b"\x01\x02"

    def test_encode_dict_as_json(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient

        result = MQTTClient._encode_payload({"temp": 25.0})
        assert json.loads(result) == {"temp": 25.0}

    def test_encode_list_as_json(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient

        result = MQTTClient._encode_payload([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]

    def test_encode_scalar_as_string(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient

        assert MQTTClient._encode_payload(42) == b"42"
        assert MQTTClient._encode_payload(3.14) == b"3.14"
        assert MQTTClient._encode_payload(True) == b"True"

    def test_decode_json_object(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient

        result = MQTTClient._decode_payload(b'{"temp": 25.0}')
        assert result == {"temp": 25.0}

    def test_decode_integer(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient

        assert MQTTClient._decode_payload(b"42") == 42

    def test_decode_float(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient

        assert MQTTClient._decode_payload(b"3.14") == 3.14

    def test_decode_boolean(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient

        assert MQTTClient._decode_payload(b"true") is True
        assert MQTTClient._decode_payload(b"false") is False

    def test_decode_plain_string(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient

        assert MQTTClient._decode_payload(b"hello world") == "hello world"


# ═══════════════════════════════════════════════════════════════════════════
#  MQTTClient Lifecycle Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestMQTTClientLifecycle:
    """Test connect, disconnect, and health_check."""

    @pytest.mark.asyncio
    async def test_connect_missing_aiomqtt_raises(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None)
        client = MQTTClient(settings)

        with patch.dict("sys.modules", {"aiomqtt": None}):
            with pytest.raises(EquipmentConnectionError, match="aiomqtt"):
                await client.connect()

    @pytest.mark.asyncio
    async def test_connect_success(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None)
        client = MQTTClient(settings)

        mock_mqtt_client = AsyncMock()
        mock_mqtt_client.__aenter__ = AsyncMock(return_value=mock_mqtt_client)
        mock_mqtt_client.__aexit__ = AsyncMock(return_value=None)
        mock_mqtt_client.subscribe = AsyncMock()
        mock_mqtt_client.messages = _empty_async_iter()

        fake_aiomqtt = _make_fake_aiomqtt(mock_mqtt_client)
        with patch.dict("sys.modules", {"aiomqtt": fake_aiomqtt}):
            with patch.object(client, "_listen_loop", new=_noop_coro):
                await client.connect()

        assert client._connected is True
        mock_mqtt_client.subscribe.assert_called()

    @pytest.mark.asyncio
    async def test_connect_with_username(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(
            _env_file=None,
            EQUIP_MQTT_USERNAME="user1",
            EQUIP_MQTT_PASSWORD="pass1",
        )
        client = MQTTClient(settings)

        captured_kwargs = {}

        def mock_client_constructor(**kwargs):
            captured_kwargs.update(kwargs)
            mock_inst = AsyncMock()
            mock_inst.__aenter__ = AsyncMock(return_value=mock_inst)
            mock_inst.__aexit__ = AsyncMock(return_value=None)
            mock_inst.subscribe = AsyncMock()
            mock_inst.messages = _empty_async_iter()
            return mock_inst

        fake_aiomqtt = _make_fake_aiomqtt(constructor=mock_client_constructor)
        with patch.dict("sys.modules", {"aiomqtt": fake_aiomqtt}):
            with patch.object(client, "_listen_loop", new=_noop_coro):
                await client.connect()

        assert captured_kwargs["username"] == "user1"
        assert captured_kwargs["password"] == "pass1"

    @pytest.mark.asyncio
    async def test_connect_with_tls(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(
            _env_file=None,
            EQUIP_MQTT_USE_TLS=True,
        )
        client = MQTTClient(settings)

        captured_kwargs = {}

        def mock_client_constructor(**kwargs):
            captured_kwargs.update(kwargs)
            mock_inst = AsyncMock()
            mock_inst.__aenter__ = AsyncMock(return_value=mock_inst)
            mock_inst.__aexit__ = AsyncMock(return_value=None)
            mock_inst.subscribe = AsyncMock()
            mock_inst.messages = _empty_async_iter()
            return mock_inst

        fake_aiomqtt = _make_fake_aiomqtt(constructor=mock_client_constructor)
        with patch.dict("sys.modules", {"aiomqtt": fake_aiomqtt}):
            with patch.object(client, "_listen_loop", new=_noop_coro):
                await client.connect()

        assert "tls_context" in captured_kwargs
        assert isinstance(captured_kwargs["tls_context"], ssl.SSLContext)

    @pytest.mark.asyncio
    async def test_connect_failure_raises(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None)
        client = MQTTClient(settings)

        mock_mqtt_client = AsyncMock()
        mock_mqtt_client.__aenter__ = AsyncMock(side_effect=ConnectionRefusedError("refused"))

        fake_aiomqtt = _make_fake_aiomqtt(mock_mqtt_client)
        with patch.dict("sys.modules", {"aiomqtt": fake_aiomqtt}):
            with pytest.raises(EquipmentConnectionError, match="connection failed"):
                await client.connect()

        assert client._connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient, _CachedValue
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None)
        client = MQTTClient(settings)

        # Simulate connected state
        client._connected = True
        client._client = AsyncMock()
        client._client.__aexit__ = AsyncMock(return_value=None)
        client._tag_cache["temp"] = _CachedValue(
            value=25.0, quality="good", data_type="float",
            timestamp=datetime.now(timezone.utc),
        )
        client._callbacks["temp"] = lambda x: None
        client._listener_task = None

        await client.disconnect()

        assert client._connected is False
        assert len(client._tag_cache) == 0
        assert len(client._callbacks) == 0

    @pytest.mark.asyncio
    async def test_health_check_connected(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None)
        client = MQTTClient(settings)
        client._connected = True
        client._client = MagicMock()

        assert await client.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None)
        client = MQTTClient(settings)
        client._connected = False

        assert await client.health_check() is False


# ═══════════════════════════════════════════════════════════════════════════
#  MQTTClient Tag Operations
# ═══════════════════════════════════════════════════════════════════════════

class TestMQTTClientTagOps:
    """Test read_tag, write_tag, subscribe_tag, unsubscribe_tag."""

    @pytest.mark.asyncio
    async def test_read_tag_from_cache(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient, _CachedValue
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None)
        client = MQTTClient(settings)
        client._tag_cache["temperature"] = _CachedValue(
            value=25.5, quality="good", data_type="float",
            timestamp=datetime.now(timezone.utc),
        )

        value, quality, data_type = await client.read_tag("temperature")
        assert value == 25.5
        assert quality == "good"
        assert data_type == "float"

    @pytest.mark.asyncio
    async def test_read_tag_not_found(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None)
        client = MQTTClient(settings)

        with pytest.raises(TagNotFoundError):
            await client.read_tag("nonexistent")

    @pytest.mark.asyncio
    async def test_write_tag_publishes(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None, EQUIP_MQTT_TOPIC_PREFIX="mes/equip")
        client = MQTTClient(settings)
        client._connected = True
        client._client = AsyncMock()
        client._client.publish = AsyncMock()

        await client.write_tag("temperature", 30.0)

        client._client.publish.assert_called_once()
        call_args = client._client.publish.call_args
        assert call_args.args[0] == "mes/equip/temperature"
        assert call_args.kwargs["payload"] == b"30.0"
        assert call_args.kwargs["retain"] is True

    @pytest.mark.asyncio
    async def test_write_tag_not_connected(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None)
        client = MQTTClient(settings)
        client._connected = False

        with pytest.raises(EquipmentConnectionError, match="not connected"):
            await client.write_tag("temperature", 30.0)

    @pytest.mark.asyncio
    async def test_write_tag_timeout(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None, EQUIP_MQTT_TIMEOUT=1)
        client = MQTTClient(settings)
        client._connected = True
        client._client = AsyncMock()
        client._client.publish = AsyncMock(side_effect=asyncio.TimeoutError)

        with pytest.raises(CommunicationTimeoutError, match="Timeout"):
            await client.write_tag("temperature", 30.0)

    @pytest.mark.asyncio
    async def test_subscribe_tag_registers_callback(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None)
        client = MQTTClient(settings)

        callback = MagicMock()
        handle_id = await client.subscribe_tag("temperature", callback, 1000)

        assert handle_id == "temperature"
        assert client._callbacks["temperature"] is callback

    @pytest.mark.asyncio
    async def test_unsubscribe_tag_removes_callback(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None)
        client = MQTTClient(settings)
        client._callbacks["temperature"] = MagicMock()

        await client.unsubscribe_tag("temperature")

        assert "temperature" not in client._callbacks


# ═══════════════════════════════════════════════════════════════════════════
#  MQTTClient Topic/Tag Mapping
# ═══════════════════════════════════════════════════════════════════════════

class TestTopicTagMapping:
    """Test _tag_to_topic and _topic_to_tag conversions."""

    def test_tag_to_topic_simple(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None, EQUIP_MQTT_TOPIC_PREFIX="mes/equip")
        client = MQTTClient(settings)

        assert client._tag_to_topic("temperature") == "mes/equip/temperature"

    def test_tag_to_topic_already_full(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None, EQUIP_MQTT_TOPIC_PREFIX="mes/equip")
        client = MQTTClient(settings)

        assert client._tag_to_topic("mes/equip/temperature") == "mes/equip/temperature"

    def test_topic_to_tag_strips_prefix(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None, EQUIP_MQTT_TOPIC_PREFIX="mes/equip")
        client = MQTTClient(settings)

        assert client._topic_to_tag("mes/equip/temperature") == "temperature"

    def test_topic_to_tag_no_prefix(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None, EQUIP_MQTT_TOPIC_PREFIX="mes/equip")
        client = MQTTClient(settings)

        assert client._topic_to_tag("other/topic") == "other/topic"

    def test_nested_tag(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None, EQUIP_MQTT_TOPIC_PREFIX="mes/equip")
        client = MQTTClient(settings)

        assert client._tag_to_topic("sensors/temp1") == "mes/equip/sensors/temp1"
        assert client._topic_to_tag("mes/equip/sensors/temp1") == "sensors/temp1"


# ═══════════════════════════════════════════════════════════════════════════
#  MQTTClient Browse
# ═══════════════════════════════════════════════════════════════════════════

class TestMQTTClientBrowse:
    """Test browse() returning cached tags."""

    @pytest.mark.asyncio
    async def test_browse_empty(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None)
        client = MQTTClient(settings)

        result = await client.browse()
        assert result == []

    @pytest.mark.asyncio
    async def test_browse_with_cached_tags(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient, _CachedValue
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None, EQUIP_MQTT_TOPIC_PREFIX="mes/equip")
        client = MQTTClient(settings)
        now = datetime.now(timezone.utc)
        client._tag_cache["temperature"] = _CachedValue(
            value=25.0, quality="good", data_type="float", timestamp=now,
        )
        client._tag_cache["running"] = _CachedValue(
            value=True, quality="good", data_type="bool", timestamp=now,
        )

        result = await client.browse()
        assert len(result) == 2
        names = {t["tag_name"] for t in result}
        assert names == {"temperature", "running"}


# ═══════════════════════════════════════════════════════════════════════════
#  MQTTClient Read State Topic
# ═══════════════════════════════════════════════════════════════════════════

class TestMQTTClientReadStateTopic:
    """Test read_state_topic()."""

    @pytest.mark.asyncio
    async def test_no_state_topic_configured(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None, EQUIP_MQTT_STATE_TOPIC="")
        client = MQTTClient(settings)

        result = await client.read_state_topic()
        assert result is None

    @pytest.mark.asyncio
    async def test_state_topic_returns_cached(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient, _CachedValue
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(
            _env_file=None,
            EQUIP_MQTT_TOPIC_PREFIX="mes/equip",
            EQUIP_MQTT_STATE_TOPIC="mes/equip/state",
        )
        client = MQTTClient(settings)
        client._tag_cache["state"] = _CachedValue(
            value="running", quality="good", data_type="string",
            timestamp=datetime.now(timezone.utc),
        )

        result = await client.read_state_topic()
        assert result == "running"

    @pytest.mark.asyncio
    async def test_state_topic_no_value(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(
            _env_file=None,
            EQUIP_MQTT_STATE_TOPIC="mes/equip/state",
            EQUIP_MQTT_TOPIC_PREFIX="mes/equip",
        )
        client = MQTTClient(settings)
        # No cached value

        result = await client.read_state_topic()
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════
#  Listener Loop Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestListenerLoop:
    """Test the _listen_loop message handling."""

    @pytest.mark.asyncio
    async def test_message_updates_cache(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None, EQUIP_MQTT_TOPIC_PREFIX="mes/equip")
        client = MQTTClient(settings)

        # Simulate a message by directly calling what _listen_loop would do
        msg = SimpleNamespace(
            topic=SimpleNamespace(__str__=lambda self: "mes/equip/temperature"),
            payload=b"25.5",
        )
        # Patch str() on topic
        msg.topic = _MockTopic("mes/equip/temperature")

        # Simulate processing (extracted from _listen_loop logic)
        from mes.adapters.equipment.mqtt.client import _infer_python_type, _CachedValue

        topic_str = str(msg.topic)
        tag_name = client._topic_to_tag(topic_str)
        value = MQTTClient._decode_payload(msg.payload)
        data_type = _infer_python_type(value)
        client._tag_cache[tag_name] = _CachedValue(
            value=value, quality="good", data_type=data_type,
            timestamp=datetime.now(timezone.utc),
        )

        assert "temperature" in client._tag_cache
        assert client._tag_cache["temperature"].value == 25.5

    @pytest.mark.asyncio
    async def test_message_dispatches_callback(self):
        from mes.adapters.equipment.mqtt.client import MQTTClient, _CachedValue, _infer_python_type
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None, EQUIP_MQTT_TOPIC_PREFIX="mes/equip")
        client = MQTTClient(settings)

        received_values = []
        client._callbacks["temperature"] = lambda tv: received_values.append(tv)

        # Simulate message processing
        topic_str = "mes/equip/temperature"
        tag_name = client._topic_to_tag(topic_str)
        value = MQTTClient._decode_payload(b"30.0")
        data_type = _infer_python_type(value)
        client._tag_cache[tag_name] = _CachedValue(
            value=value, quality="good", data_type=data_type,
            timestamp=datetime.now(timezone.utc),
        )

        callback = client._callbacks.get(tag_name)
        if callback:
            tag_value = TagValue(
                tag_name=tag_name, value=value, quality="good",
                data_type=data_type,
            )
            callback(tag_value)

        assert len(received_values) == 1
        assert received_values[0].value == 30.0
        assert received_values[0].tag_name == "temperature"


# ═══════════════════════════════════════════════════════════════════════════
#  MQTTEquipmentAdapter Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestMQTTEquipmentAdapter:
    """Test the MQTTEquipmentAdapter delegating to MQTTClient."""

    def _make_adapter(self):
        from mes.adapters.equipment.mqtt.adapter import MQTTEquipmentAdapter
        from mes.adapters.equipment.mqtt.config import MQTTSettings

        settings = MQTTSettings(_env_file=None, EQUIP_MQTT_EQUIPMENT_ID="TEST-MQTT-01")
        adapter = MQTTEquipmentAdapter(settings)
        adapter._client = AsyncMock()
        return adapter

    def test_equipment_id(self):
        adapter = self._make_adapter()
        assert adapter.equipment_id == "TEST-MQTT-01"

    @pytest.mark.asyncio
    async def test_connect_delegates(self):
        adapter = self._make_adapter()
        await adapter.connect()
        adapter._client.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_delegates(self):
        adapter = self._make_adapter()
        await adapter.disconnect()
        adapter._client.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_health_check_delegates(self):
        adapter = self._make_adapter()
        adapter._client.health_check.return_value = True
        result = await adapter.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_read_tag(self):
        adapter = self._make_adapter()
        adapter._client.read_tag.return_value = (25.5, "good", "float")

        tag_value = await adapter.read_tag("temperature")

        assert isinstance(tag_value, TagValue)
        assert tag_value.tag_name == "temperature"
        assert tag_value.value == 25.5
        assert tag_value.quality == "good"
        assert tag_value.data_type == "float"

    @pytest.mark.asyncio
    async def test_write_tag(self):
        adapter = self._make_adapter()
        await adapter.write_tag("temperature", 30.0)
        adapter._client.write_tag.assert_awaited_once_with("temperature", 30.0)

    @pytest.mark.asyncio
    async def test_subscribe_tag(self):
        adapter = self._make_adapter()
        adapter._client.subscribe_tag.return_value = "temperature"

        callback = MagicMock()
        handle = await adapter.subscribe_tag("temperature", callback, 1000)

        assert isinstance(handle, SubscriptionHandle)
        assert handle.tag_name == "temperature"
        assert handle.active is True

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        adapter = self._make_adapter()
        handle = SubscriptionHandle(handle_id="temperature", tag_name="temperature", active=True)
        adapter._subscriptions["temperature"] = handle

        await adapter.unsubscribe(handle)

        assert handle.active is False
        assert "temperature" not in adapter._subscriptions
        adapter._client.unsubscribe_tag.assert_awaited_once_with("temperature")

    @pytest.mark.asyncio
    async def test_browse_tags(self):
        adapter = self._make_adapter()
        adapter._client.browse.return_value = [
            {"tag_name": "temp", "data_type": "float", "access": "readwrite", "description": "Temperature"},
            {"tag_name": "speed", "data_type": "int", "access": "read", "description": "Speed"},
        ]

        tags = await adapter.browse_tags()

        assert len(tags) == 2
        assert all(isinstance(t, TagInfo) for t in tags)
        assert tags[0].tag_name == "temp"
        assert tags[1].access == "read"

    @pytest.mark.asyncio
    async def test_get_equipment_state(self):
        adapter = self._make_adapter()
        adapter._client.read_state_topic.return_value = "running"

        state = await adapter.get_equipment_state()

        assert isinstance(state, EquipmentState)
        assert state.state == "running"
        assert state.dispatch_category == "busy"
        assert state.oee_bucket == "uptime_value_add"
        assert state.equipment_id == "TEST-MQTT-01"


# ═══════════════════════════════════════════════════════════════════════════
#  State Mapping Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestEquipmentStateMapping:
    """Test the state → dispatch/OEE mappings."""

    def test_running_state(self):
        from mes.adapters.equipment.mqtt.adapter import _STATE_DISPATCH_MAP, _STATE_OEE_MAP

        assert _STATE_DISPATCH_MAP["running"] == "busy"
        assert _STATE_OEE_MAP["running"] == "uptime_value_add"

    def test_idle_state(self):
        from mes.adapters.equipment.mqtt.adapter import _STATE_DISPATCH_MAP, _STATE_OEE_MAP

        assert _STATE_DISPATCH_MAP["idle"] == "available"
        assert _STATE_OEE_MAP["idle"] == "uptime_non_value"

    def test_fault_state(self):
        from mes.adapters.equipment.mqtt.adapter import _STATE_DISPATCH_MAP, _STATE_OEE_MAP

        assert _STATE_DISPATCH_MAP["fault"] == "unavailable_unplanned"
        assert _STATE_OEE_MAP["fault"] == "downtime_unplanned"

    def test_maintenance_state(self):
        from mes.adapters.equipment.mqtt.adapter import _STATE_DISPATCH_MAP, _STATE_OEE_MAP

        assert _STATE_DISPATCH_MAP["maintenance"] == "unavailable_planned"
        assert _STATE_OEE_MAP["maintenance"] == "downtime_planned"

    def test_unknown_state_defaults(self):
        from mes.adapters.equipment.mqtt.adapter import _STATE_DISPATCH_MAP, _STATE_OEE_MAP

        assert _STATE_DISPATCH_MAP.get("unknown", "available") == "available"
        assert _STATE_OEE_MAP.get("unknown", "uptime_non_value") == "uptime_non_value"

    def test_all_map_entries_consistent(self):
        from mes.adapters.equipment.mqtt.adapter import _STATE_DISPATCH_MAP, _STATE_OEE_MAP

        assert set(_STATE_DISPATCH_MAP.keys()) == set(_STATE_OEE_MAP.keys())


# ═══════════════════════════════════════════════════════════════════════════
#  Test Helpers
# ═══════════════════════════════════════════════════════════════════════════

class _MockTopic:
    """Mock MQTT topic that converts to string correctly."""

    def __init__(self, name: str) -> None:
        self._name = name

    def __str__(self) -> str:
        return self._name


async def _empty_async_iter():
    """Async iterator that yields nothing (for mocking client.messages)."""
    return
    yield  # Make it an async generator  # noqa: RET504


async def _noop_coro():
    """No-op coroutine for mocking _listen_loop."""
    pass


def _make_fake_aiomqtt(client_instance=None, constructor=None):
    """Create a fake aiomqtt module for sys.modules injection."""
    fake_module = MagicMock()
    if constructor:
        fake_module.Client = constructor
    elif client_instance:
        fake_module.Client = MagicMock(return_value=client_instance)
    else:
        fake_module.Client = MagicMock()
    return fake_module
