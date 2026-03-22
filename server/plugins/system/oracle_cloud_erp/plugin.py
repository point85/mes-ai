"""
Oracle Cloud ERP Adapter Plugin.

Wraps the Oracle Cloud ERP inbound and outbound adapters as a unified
plugin managed by the plugin framework.

The underlying adapter classes read their configuration from
MES_ERP_* and MES_ORACLE_* environment variables via pydantic-settings.
"""

from __future__ import annotations

from typing import Any

from mes.framework.plugin import MESPlugin


class OracleCloudERPPlugin(MESPlugin):
    """Plugin wrapper for the Oracle Cloud ERP adapter pair."""

    def __init__(self) -> None:
        self._inbound: Any = None
        self._outbound: Any = None

    async def initialize(self, config: dict[str, Any]) -> None:
        from mes.adapters.erp.oracle.adapter import (
            OracleInboundAdapter,
            OracleOutboundAdapter,
        )
        self._inbound = OracleInboundAdapter()
        self._outbound = OracleOutboundAdapter()

    async def start(self) -> None:
        if self._inbound:
            await self._inbound.connect()
        if self._outbound:
            await self._outbound.connect()

    async def stop(self) -> None:
        if self._inbound:
            await self._inbound.disconnect()
        if self._outbound:
            await self._outbound.disconnect()

    async def health_check(self) -> bool:
        ib = await self._inbound.health_check() if self._inbound else False
        ob = await self._outbound.health_check() if self._outbound else False
        return ib and ob

    def get_adapter(self) -> dict[str, Any]:
        return {
            "erp_inbound": self._inbound,
            "erp_outbound": self._outbound,
        }
