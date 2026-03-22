"""
OPC-UA Equipment Adapter Plugin.

Wraps the OPC-UA equipment adapter as a plugin
managed by the plugin framework.

The underlying adapter class reads its configuration from
MES_EQUIP_OPCUA_* environment variables via pydantic-settings.
"""

from __future__ import annotations

from typing import Any

from mes.framework.plugin import MESPlugin


class OPCUAEquipmentPlugin(MESPlugin):
    """Plugin wrapper for the OPC-UA equipment adapter."""

    def __init__(self) -> None:
        self._adapter: Any = None

    async def initialize(self, config: dict[str, Any]) -> None:
        from mes.adapters.equipment.opcua.adapter import OPCUAEquipmentAdapter
        self._adapter = OPCUAEquipmentAdapter()

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
