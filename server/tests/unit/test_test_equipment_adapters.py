"""
Unit tests for Test Equipment integration adapters.

Covers:
- TestResultDTO dataclass construction
- MockTestEquipmentAdapter (result generation, pass rate, subscriptions)
- Exception construction and error codes
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from mes.adapters.equipment.dtos import SubscriptionHandle
from mes.adapters.test_equipment.dtos import TestResultDTO
from mes.adapters.test_equipment.exceptions import (
    ResultParsingError,
    TestEquipmentConnectionError,
)
from mes.adapters.test_equipment.mock_adapter import MockTestEquipmentAdapter


# ═══════════════════════════════════════════════════════════════════
# DTO Tests
# ═══════════════════════════════════════════════════════════════════


class TestTestResultDTO:
    def test_minimal(self):
        dto = TestResultDTO(test_id="T-001", equipment_id="EQ-1")
        assert dto.result == "pass"
        assert dto.unit_serial is None
        assert dto.measured_values == {}
        assert isinstance(dto.timestamp, datetime)

    def test_full(self):
        now = datetime.now(timezone.utc)
        dto = TestResultDTO(
            test_id="T-002",
            equipment_id="EQ-1",
            unit_serial="SN-001",
            lot_number="LOT-A",
            result="fail",
            measured_values={"length": 10.1, "weight": 50.2},
            timestamp=now,
            metadata={"operator": "JD"},
        )
        assert dto.result == "fail"
        assert dto.measured_values["length"] == 10.1
        assert dto.metadata["operator"] == "JD"


# ═══════════════════════════════════════════════════════════════════
# Mock Test Equipment Adapter
# ═══════════════════════════════════════════════════════════════════


class TestMockTestEquipmentAdapter:
    @pytest.fixture
    def adapter(self):
        return MockTestEquipmentAdapter(
            equipment_id="TEST-STATION-01",
            pass_rate=0.9,
            measurements={"length": (9.8, 10.2), "weight": (49.5, 50.5)},
        )

    @pytest.mark.asyncio
    async def test_lifecycle(self, adapter):
        assert await adapter.health_check() is False
        await adapter.connect()
        assert await adapter.health_check() is True
        await adapter.disconnect()
        assert await adapter.health_check() is False

    @pytest.mark.asyncio
    async def test_get_test_result(self, adapter):
        await adapter.connect()
        result = await adapter.get_test_result("T-001")
        assert isinstance(result, TestResultDTO)
        assert result.test_id == "T-001"
        assert result.equipment_id == "TEST-STATION-01"
        assert "length" in result.measured_values
        assert "weight" in result.measured_values
        assert result.result in ("pass", "fail")

    @pytest.mark.asyncio
    async def test_result_counter(self, adapter):
        await adapter.connect()
        assert adapter.result_count == 0
        await adapter.get_test_result("T-1")
        await adapter.get_test_result("T-2")
        assert adapter.result_count == 2

    @pytest.mark.asyncio
    async def test_auto_test_id(self, adapter):
        await adapter.connect()
        r = await adapter.get_test_result("auto")
        assert r.test_id == "TEST-0001"

    @pytest.mark.asyncio
    async def test_subscribe_and_notify(self, adapter):
        await adapter.connect()
        received = []
        callback = MagicMock(side_effect=lambda r: received.append(r))

        handle = await adapter.subscribe_results(callback)
        assert isinstance(handle, SubscriptionHandle)
        assert handle.active is True

        adapter.generate_and_notify(test_id="T-SUB", unit_serial="SN-99")
        assert len(received) == 1
        assert received[0].test_id == "T-SUB"
        assert received[0].unit_serial == "SN-99"

    @pytest.mark.asyncio
    async def test_get_test_status(self, adapter):
        await adapter.connect()
        status = await adapter.get_test_status("any")
        assert status == "idle"

    def test_set_status(self, adapter):
        adapter.set_status("running")
        assert adapter._status == "running"

    @pytest.mark.asyncio
    async def test_watch_directory_noop(self, adapter):
        await adapter.connect()
        # Should not raise
        await adapter.watch_directory("/tmp/test", "*.csv")

    @pytest.mark.asyncio
    async def test_disconnect_clears_subscribers(self, adapter):
        await adapter.connect()
        callback = MagicMock()
        handle = await adapter.subscribe_results(callback)
        await adapter.disconnect()
        assert handle.active is False

    @pytest.mark.asyncio
    async def test_measurement_ranges(self, adapter):
        """Verify generated measurements fall within configured ranges."""
        await adapter.connect()
        for _ in range(50):
            r = await adapter.get_test_result("T-RANGE")
            assert 9.8 <= r.measured_values["length"] <= 10.2
            assert 49.5 <= r.measured_values["weight"] <= 50.5


class TestMockTestEquipmentPassRate:
    @pytest.mark.asyncio
    async def test_all_pass(self):
        adapter = MockTestEquipmentAdapter(pass_rate=1.0)
        await adapter.connect()
        results = [await adapter.get_test_result(f"T-{i}") for i in range(50)]
        assert all(r.result == "pass" for r in results)

    @pytest.mark.asyncio
    async def test_all_fail(self):
        adapter = MockTestEquipmentAdapter(pass_rate=0.0)
        await adapter.connect()
        results = [await adapter.get_test_result(f"T-{i}") for i in range(50)]
        assert all(r.result == "fail" for r in results)


# ═══════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════


class TestTestEquipmentExceptions:
    def test_connection_error(self):
        exc = TestEquipmentConnectionError()
        assert exc.status_code == 502
        assert exc.error_code == "TEST_EQUIPMENT_CONNECTION_ERROR"

    def test_result_parsing_error(self):
        exc = ResultParsingError(message="bad CSV")
        assert exc.status_code == 422
        assert exc.error_code == "RESULT_PARSING_ERROR"
        assert "bad CSV" in str(exc)
