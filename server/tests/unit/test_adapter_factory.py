"""
Unit tests for AdapterFactory.

Covers:
- Factory creates mock adapters when config says "mock"
- Factory returns None for "none" adapters
- connect_all / disconnect_all lifecycle
- health_check reporting
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from mes.adapters.factory import AdapterFactory


def _settings_override(**overrides):
    """Return a patch context manager for settings attributes."""
    return patch.multiple("mes.adapters.factory.settings", **overrides)


class TestAdapterFactoryMock:
    @pytest.mark.asyncio
    async def test_erp_mock_creates_adapters(self):
        with _settings_override(
            ERP_ADAPTER="mock",
            ERP_MOCK_LATENCY_MS=0,
            ERP_MOCK_FAILURE_RATE=0.0,
            EQUIP_ADAPTER="none",
            TEST_EQUIP_ADAPTER="none",
        ):
            factory = AdapterFactory()
            await factory.create_adapters()

            assert factory.erp_inbound is not None
            assert factory.erp_outbound is not None
            assert factory.equipment is None
            assert factory.test_equipment is None

    @pytest.mark.asyncio
    async def test_equipment_mock_creates_adapter(self):
        with _settings_override(
            ERP_ADAPTER="none",
            EQUIP_ADAPTER="mock",
            EQUIP_MOCK_LATENCY_MS=0,
            EQUIP_MOCK_FAILURE_RATE=0.0,
            TEST_EQUIP_ADAPTER="none",
        ):
            factory = AdapterFactory()
            await factory.create_adapters()

            assert factory.erp_inbound is None
            assert factory.equipment is not None

    @pytest.mark.asyncio
    async def test_test_equip_mock_creates_adapter(self):
        with _settings_override(
            ERP_ADAPTER="none",
            EQUIP_ADAPTER="none",
            TEST_EQUIP_ADAPTER="mock",
        ):
            factory = AdapterFactory()
            await factory.create_adapters()

            assert factory.test_equipment is not None

    @pytest.mark.asyncio
    async def test_none_creates_no_adapters(self):
        with _settings_override(
            ERP_ADAPTER="none",
            EQUIP_ADAPTER="none",
            TEST_EQUIP_ADAPTER="none",
        ):
            factory = AdapterFactory()
            await factory.create_adapters()

            assert factory.erp_inbound is None
            assert factory.erp_outbound is None
            assert factory.equipment is None
            assert factory.test_equipment is None

    @pytest.mark.asyncio
    async def test_unknown_adapter_falls_back_to_none(self):
        with _settings_override(
            ERP_ADAPTER="unknown_vendor",
            EQUIP_ADAPTER="unknown_proto",
            TEST_EQUIP_ADAPTER="unknown_type",
        ):
            factory = AdapterFactory()
            await factory.create_adapters()

            assert factory.erp_inbound is None
            assert factory.equipment is None
            assert factory.test_equipment is None


class TestAdapterFactoryLifecycle:
    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        with _settings_override(
            ERP_ADAPTER="mock",
            ERP_MOCK_LATENCY_MS=0,
            ERP_MOCK_FAILURE_RATE=0.0,
            EQUIP_ADAPTER="mock",
            EQUIP_MOCK_LATENCY_MS=0,
            EQUIP_MOCK_FAILURE_RATE=0.0,
            TEST_EQUIP_ADAPTER="mock",
        ):
            factory = AdapterFactory()
            await factory.connect_all()

            health = await factory.health_check()
            assert health["erp_inbound"] is True
            assert health["erp_outbound"] is True
            assert health["equipment"] is True
            assert health["test_equipment"] is True

            await factory.disconnect_all()

            health = await factory.health_check()
            assert health["erp_inbound"] is False
            assert health["erp_outbound"] is False

    @pytest.mark.asyncio
    async def test_health_check_empty_factory(self):
        with _settings_override(
            ERP_ADAPTER="none",
            EQUIP_ADAPTER="none",
            TEST_EQUIP_ADAPTER="none",
        ):
            factory = AdapterFactory()
            await factory.connect_all()
            health = await factory.health_check()
            assert health == {}


class TestAdapterFactoryAllMock:
    @pytest.mark.asyncio
    async def test_all_mock(self):
        with _settings_override(
            ERP_ADAPTER="mock",
            ERP_MOCK_LATENCY_MS=0,
            ERP_MOCK_FAILURE_RATE=0.0,
            EQUIP_ADAPTER="mock",
            EQUIP_MOCK_LATENCY_MS=0,
            EQUIP_MOCK_FAILURE_RATE=0.0,
            TEST_EQUIP_ADAPTER="mock",
        ):
            factory = AdapterFactory()
            await factory.connect_all()

            assert factory.erp_inbound is not None
            assert factory.erp_outbound is not None
            assert factory.equipment is not None
            assert factory.test_equipment is not None

            await factory.disconnect_all()
