"""
Mock Equipment Adapter Plugin.

Wraps the built-in MockEquipmentAdapter as a plugin
managed by the plugin framework.
"""

from __future__ import annotations

from typing import Any

from mes.adapters.equipment.mock_adapter import MockEquipmentAdapter
from mes.framework.plugin import MESPlugin


class MockEquipmentPlugin(MESPlugin):
    """Plugin wrapper for the mock equipment adapter."""

    def __init__(self) -> None:
        self._adapter: MockEquipmentAdapter | None = None

    async def initialize(self, config: dict[str, Any]) -> None:
        self._adapter = MockEquipmentAdapter(
            equipment_id=config.get("equipment_id", "MOCK-EQUIP-01"),
            initial_tags={
                "temperature": 25.0,
                "pressure": 1.0,
                "speed": 100,
                "running": True,
            },
            noise_stddev=float(config.get("noise_stddev", 0.1)),
            latency_ms=int(config.get("latency_ms", 0)),
            failure_rate=float(config.get("failure_rate", 0.0)),
        )

    async def start(self) -> None:
        if self._adapter:
            await self._adapter.connect()

    async def stop(self) -> None:
        if self._adapter:
            await self._adapter.disconnect()

    async def health_check(self) -> bool:
        return await self._adapter.health_check() if self._adapter else False

    def get_adapter(self) -> Any:
        return self._adapter
