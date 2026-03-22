"""
Mock Test Equipment Adapter Plugin.

Wraps the built-in MockTestEquipmentAdapter as a plugin
managed by the plugin framework.
"""

from __future__ import annotations

from typing import Any

from mes.adapters.test_equipment.mock_adapter import MockTestEquipmentAdapter
from mes.framework.plugin import MESPlugin


class MockTestEquipmentPlugin(MESPlugin):
    """Plugin wrapper for the mock test equipment adapter."""

    def __init__(self) -> None:
        self._adapter: MockTestEquipmentAdapter | None = None

    async def initialize(self, config: dict[str, Any]) -> None:
        self._adapter = MockTestEquipmentAdapter(
            equipment_id=config.get("equipment_id", "MOCK-TEST-01"),
            pass_rate=float(config.get("pass_rate", 0.9)),
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
