"""
SAP S/4HANA ERP Adapter Plugin.

Wraps the SAP S/4HANA inbound and outbound adapters as a unified
plugin managed by the plugin framework.

The underlying adapter classes read their configuration from
MES_ERP_* and MES_SAP_* environment variables via pydantic-settings.
"""

from __future__ import annotations

from typing import Any

from mes.framework.plugin import MESPlugin


class SAPS4HANAPlugin(MESPlugin):
    """Plugin wrapper for the SAP S/4HANA ERP adapter pair."""

    def __init__(self) -> None:
        self._inbound: Any = None
        self._outbound: Any = None

    async def initialize(self, config: dict[str, Any]) -> None:
        from mes.adapters.erp.sap_s4hana.adapter import (
            SAPS4HANAInboundAdapter,
            SAPS4HANAOutboundAdapter,
        )
        self._inbound = SAPS4HANAInboundAdapter()
        self._outbound = SAPS4HANAOutboundAdapter()

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
