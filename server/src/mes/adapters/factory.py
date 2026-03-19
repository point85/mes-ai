"""
Integration Adapters: Factory for creating adapter instances from configuration.

AdapterFactory reads MES_ERP_ADAPTER and MES_EQUIP_ADAPTER config values to
instantiate the appropriate adapter implementations (mock or vendor-specific).

Per ARCHITECTURE.md §9.2.8 and §9.3.3.
"""

from __future__ import annotations

import logging
from typing import Any

from mes.config import settings

logger = logging.getLogger("mes.adapters.factory")


class AdapterFactory:
    """
    Creates and manages adapter instances based on application configuration.

    Usage:
        factory = AdapterFactory()
        await factory.connect_all()      # Called during app startup
        inbound = factory.erp_inbound    # Access adapter instances
        await factory.disconnect_all()   # Called during app shutdown
    """

    def __init__(self) -> None:
        self._erp_inbound: Any = None
        self._erp_outbound: Any = None
        self._equipment: Any = None
        self._test_equipment: Any = None

    @property
    def erp_inbound(self) -> Any:
        return self._erp_inbound

    @property
    def erp_outbound(self) -> Any:
        return self._erp_outbound

    @property
    def equipment(self) -> Any:
        return self._equipment

    @property
    def test_equipment(self) -> Any:
        return self._test_equipment

    async def create_adapters(self) -> None:
        """Instantiate adapter instances from configuration."""
        self._erp_inbound, self._erp_outbound = _create_erp_adapters()
        self._equipment = _create_equipment_adapter()
        self._test_equipment = _create_test_equipment_adapter()
        logger.info(
            "Adapters created: ERP=%s, Equipment=%s, TestEquipment=%s",
            settings.ERP_ADAPTER,
            settings.EQUIP_ADAPTER,
            settings.TEST_EQUIP_ADAPTER,
        )

    async def connect_all(self) -> None:
        """Connect all adapter instances."""
        await self.create_adapters()
        for name, adapter in self._get_active_adapters():
            try:
                await adapter.connect()
                logger.info("Adapter %s connected", name)
            except Exception:
                logger.exception("Failed to connect adapter %s", name)

    async def disconnect_all(self) -> None:
        """Disconnect all adapter instances."""
        for name, adapter in self._get_active_adapters():
            try:
                await adapter.disconnect()
                logger.info("Adapter %s disconnected", name)
            except Exception:
                logger.exception("Failed to disconnect adapter %s", name)

    async def health_check(self) -> dict[str, bool]:
        """Check health of all adapters."""
        results = {}
        for name, adapter in self._get_active_adapters():
            try:
                results[name] = await adapter.health_check()
            except Exception:
                results[name] = False
        return results

    def _get_active_adapters(self) -> list[tuple[str, Any]]:
        """Return list of (name, adapter) for non-None adapters."""
        adapters = []
        if self._erp_inbound:
            adapters.append(("erp_inbound", self._erp_inbound))
        if self._erp_outbound:
            adapters.append(("erp_outbound", self._erp_outbound))
        if self._equipment:
            adapters.append(("equipment", self._equipment))
        if self._test_equipment:
            adapters.append(("test_equipment", self._test_equipment))
        return adapters


def _create_erp_adapters() -> tuple[Any, Any]:
    """Create ERP inbound and outbound adapter pair."""
    adapter_type = settings.ERP_ADAPTER

    if adapter_type == "mock":
        from mes.adapters.erp.mock_adapter import (
            MockERPInboundAdapter,
            MockERPOutboundAdapter,
        )
        inbound = MockERPInboundAdapter(
            latency_ms=settings.ERP_MOCK_LATENCY_MS,
            failure_rate=settings.ERP_MOCK_FAILURE_RATE,
        )
        outbound = MockERPOutboundAdapter(
            latency_ms=settings.ERP_MOCK_LATENCY_MS,
            failure_rate=settings.ERP_MOCK_FAILURE_RATE,
        )
        return inbound, outbound

    elif adapter_type == "none":
        return None, None

    elif adapter_type == "sap_s4hana":
        from mes.adapters.erp.sap_s4hana.adapter import (
            SAPS4HANAInboundAdapter,
            SAPS4HANAOutboundAdapter,
        )
        return SAPS4HANAInboundAdapter(), SAPS4HANAOutboundAdapter()

    else:
        # Future: load vendor-specific adapter plugin
        logger.warning("ERP adapter '%s' not implemented, falling back to none", adapter_type)
        return None, None


def _create_equipment_adapter() -> Any:
    """Create equipment adapter."""
    adapter_type = settings.EQUIP_ADAPTER

    if adapter_type == "mock":
        from mes.adapters.equipment.mock_adapter import MockEquipmentAdapter
        return MockEquipmentAdapter(
            equipment_id="MOCK-EQUIP-01",
            initial_tags={
                "temperature": 25.0,
                "pressure": 1.0,
                "speed": 100,
                "running": True,
            },
            noise_stddev=0.1,
            latency_ms=settings.EQUIP_MOCK_LATENCY_MS,
            failure_rate=settings.EQUIP_MOCK_FAILURE_RATE,
        )

    elif adapter_type == "opcua":
        from mes.adapters.equipment.opcua.adapter import OPCUAEquipmentAdapter
        return OPCUAEquipmentAdapter()

    elif adapter_type == "mqtt":
        from mes.adapters.equipment.mqtt.adapter import MQTTEquipmentAdapter
        return MQTTEquipmentAdapter()

    elif adapter_type == "none":
        return None

    else:
        # Future: load protocol-specific adapter (modbus, rest)
        logger.warning("Equipment adapter '%s' not implemented, falling back to none", adapter_type)
        return None


def _create_test_equipment_adapter() -> Any:
    """Create test equipment adapter."""
    adapter_type = settings.TEST_EQUIP_ADAPTER

    if adapter_type == "mock":
        from mes.adapters.test_equipment.mock_adapter import MockTestEquipmentAdapter
        return MockTestEquipmentAdapter(
            equipment_id="MOCK-TEST-01",
            pass_rate=0.9,
        )

    elif adapter_type == "none":
        return None

    else:
        logger.warning("Test equipment adapter '%s' not implemented, falling back to none", adapter_type)
        return None
