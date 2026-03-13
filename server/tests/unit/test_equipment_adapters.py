"""
Unit tests for Equipment integration adapters.

Covers:
- DTO dataclass construction (TagValue, TagInfo, SubscriptionHandle, EquipmentState)
- MockEquipmentAdapter (tag store, read/write, subscribe, browse, state, noise)
- Exception construction and error codes
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

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
from mes.adapters.equipment.mock_adapter import MockEquipmentAdapter


# ═══════════════════════════════════════════════════════════════════
# DTO Tests
# ═══════════════════════════════════════════════════════════════════


class TestTagValue:
    def test_construction(self):
        tv = TagValue(tag_name="temp", value=25.0)
        assert tv.tag_name == "temp"
        assert tv.value == 25.0
        assert tv.quality == "good"
        assert tv.data_type == "float"
        assert isinstance(tv.timestamp, datetime)

    def test_custom_quality(self):
        tv = TagValue(tag_name="broken", value=None, quality="bad")
        assert tv.quality == "bad"


class TestTagInfo:
    def test_construction(self):
        ti = TagInfo(tag_name="pressure", data_type="float")
        assert ti.access == "readwrite"
        assert ti.description == ""


class TestSubscriptionHandle:
    def test_defaults(self):
        sh = SubscriptionHandle()
        assert sh.active is True
        assert sh.tag_name == ""
        assert sh.topic == ""
        assert len(sh.handle_id) > 0

    def test_unique_ids(self):
        h1 = SubscriptionHandle()
        h2 = SubscriptionHandle()
        assert h1.handle_id != h2.handle_id


class TestEquipmentState:
    def test_construction(self):
        es = EquipmentState(equipment_id="EQ-1", state="running")
        assert es.dispatch_category == "available"
        assert es.oee_bucket == "uptime_value_add"
        assert isinstance(es.timestamp, datetime)


# ═══════════════════════════════════════════════════════════════════
# Mock Equipment Adapter
# ═══════════════════════════════════════════════════════════════════


class TestMockEquipmentAdapter:
    @pytest.fixture
    def adapter(self):
        return MockEquipmentAdapter(
            equipment_id="TEST-EQ",
            initial_tags={"temperature": 25.0, "speed": 100, "running": True},
            noise_stddev=0.0,
            latency_ms=0,
            failure_rate=0.0,
        )

    @pytest.mark.asyncio
    async def test_lifecycle(self, adapter):
        assert await adapter.health_check() is False
        await adapter.connect()
        assert await adapter.health_check() is True
        await adapter.disconnect()
        assert await adapter.health_check() is False

    @pytest.mark.asyncio
    async def test_read_tag(self, adapter):
        await adapter.connect()
        result = await adapter.read_tag("temperature")
        assert isinstance(result, TagValue)
        assert result.tag_name == "temperature"
        assert result.value == 25.0
        assert result.quality == "good"

    @pytest.mark.asyncio
    async def test_read_tag_not_found(self, adapter):
        await adapter.connect()
        with pytest.raises(TagNotFoundError):
            await adapter.read_tag("nonexistent")

    @pytest.mark.asyncio
    async def test_write_tag_existing(self, adapter):
        await adapter.connect()
        await adapter.write_tag("temperature", 30.0)
        result = await adapter.read_tag("temperature")
        assert result.value == 30.0

    @pytest.mark.asyncio
    async def test_write_tag_new(self, adapter):
        await adapter.connect()
        await adapter.write_tag("new_tag", 42)
        result = await adapter.read_tag("new_tag")
        assert result.value == 42

    @pytest.mark.asyncio
    async def test_subscribe_tag_callback(self, adapter):
        await adapter.connect()
        received = []
        callback = MagicMock(side_effect=lambda tv: received.append(tv))

        handle = await adapter.subscribe_tag("temperature", callback)
        assert isinstance(handle, SubscriptionHandle)
        assert handle.active is True

        # Writing triggers callback
        await adapter.write_tag("temperature", 99.0)
        assert len(received) == 1
        assert received[0].value == 99.0

    @pytest.mark.asyncio
    async def test_subscribe_async_callback(self, adapter):
        await adapter.connect()
        received = []
        callback = AsyncMock(side_effect=lambda tv: received.append(tv))

        await adapter.subscribe_tag("speed", callback)
        await adapter.write_tag("speed", 200)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self, adapter):
        await adapter.connect()
        callback = MagicMock()
        handle = await adapter.subscribe_tag("temperature", callback)
        await adapter.unsubscribe(handle)

        await adapter.write_tag("temperature", 50.0)
        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_browse_tags(self, adapter):
        await adapter.connect()
        tags = await adapter.browse_tags()
        assert len(tags) == 3
        assert all(isinstance(t, TagInfo) for t in tags)
        names = [t.tag_name for t in tags]
        assert "temperature" in names

    @pytest.mark.asyncio
    async def test_browse_tags_with_filter(self, adapter):
        await adapter.connect()
        tags = await adapter.browse_tags(root="temp")
        assert len(tags) == 1
        assert tags[0].tag_name == "temperature"

    @pytest.mark.asyncio
    async def test_get_equipment_state(self, adapter):
        await adapter.connect()
        state = await adapter.get_equipment_state()
        assert isinstance(state, EquipmentState)
        assert state.equipment_id == "TEST-EQ"
        assert state.state == "idle"
        assert state.dispatch_category == "available"

    @pytest.mark.asyncio
    async def test_set_state(self, adapter):
        await adapter.connect()
        adapter.set_state("faulted")
        state = await adapter.get_equipment_state()
        assert state.state == "faulted"
        assert state.dispatch_category == "unavailable_unplanned"

    @pytest.mark.asyncio
    async def test_tag_store_direct_access(self, adapter):
        assert adapter.tag_store["temperature"] == 25.0
        adapter.tag_store["temperature"] = 99.0
        await adapter.connect()
        result = await adapter.read_tag("temperature")
        assert result.value == 99.0

    @pytest.mark.asyncio
    async def test_disconnect_clears_subscriptions(self, adapter):
        await adapter.connect()
        callback = MagicMock()
        handle = await adapter.subscribe_tag("temperature", callback)
        await adapter.disconnect()
        assert handle.active is False


class TestMockEquipmentAdapterNoise:
    @pytest.mark.asyncio
    async def test_noise_applied_to_numeric(self):
        adapter = MockEquipmentAdapter(
            initial_tags={"value": 100.0},
            noise_stddev=5.0,
            latency_ms=0,
        )
        await adapter.connect()
        # With noise, value should differ from stored value at least sometimes
        readings = []
        for _ in range(20):
            r = await adapter.read_tag("value")
            readings.append(r.value)
        # At least one reading should differ from 100.0
        assert any(v != 100.0 for v in readings)

    @pytest.mark.asyncio
    async def test_noise_not_applied_to_string(self):
        adapter = MockEquipmentAdapter(
            initial_tags={"label": "hello"},
            noise_stddev=5.0,
            latency_ms=0,
        )
        await adapter.connect()
        r = await adapter.read_tag("label")
        assert r.value == "hello"


# ═══════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════


class TestEquipmentExceptions:
    def test_connection_error(self):
        exc = EquipmentConnectionError()
        assert exc.status_code == 502
        assert exc.error_code == "EQUIPMENT_CONNECTION_ERROR"

    def test_tag_not_found(self):
        exc = TagNotFoundError(tag_name="foo.bar")
        assert exc.status_code == 404
        assert exc.error_code == "TAG_NOT_FOUND"
        assert "foo.bar" in str(exc)

    def test_communication_timeout(self):
        exc = CommunicationTimeoutError()
        assert exc.status_code == 504
        assert exc.error_code == "EQUIPMENT_TIMEOUT"
