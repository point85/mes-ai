"""
Equipment Simulator Plugin.

A thin plugin that exists solely to register a companion React client
(clients/equipment_simulator) with the MES plugin framework.  All
actual equipment-state operations are served by the existing Performance
Analysis REST API (/api/v1/performance/*) and Physical Model REST API
(/api/v1/*).
"""

from __future__ import annotations

from typing import Any

from mes.framework.plugin import MESPlugin


class AvailabilitySimulatorPlugin(MESPlugin):
    """Plugin wrapper — registers the companion GUI client."""

    async def initialize(self, config: dict[str, Any]) -> None:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    def get_adapter(self) -> dict[str, Any]:
        return {}
