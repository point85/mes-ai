"""
SAP ERP Simulator Plugin.

Wraps SAPSimulatorInboundAdapter and SAPSimulatorOutboundAdapter as a
unified plugin managed by the MES plugin framework.

Unlike the real sap_s4hana_erp plugin (which talks to a live SAP system
over OData V4), this plugin generates realistic SAP-format data in memory
and runs it through the SAPS4HANATransformLayer — exercising the full
inbound/outbound data pipeline without any external dependency.
"""

from __future__ import annotations

from typing import Any

from mes.framework.plugin import MESPlugin


class SAPERPSimulatorPlugin(MESPlugin):
    """Plugin wrapper for the SAP ERP simulator adapter pair."""

    def __init__(self) -> None:
        self._inbound: Any = None
        self._outbound: Any = None

    async def initialize(self, config: dict[str, Any]) -> None:
        from .simulator import SAPSimulatorInboundAdapter, SAPSimulatorOutboundAdapter

        plant = str(config.get("plant", "1000"))
        company_code = str(config.get("company_code", "1000"))
        latency_ms = int(config.get("latency_ms", 0))
        failure_rate = float(config.get("failure_rate", 0.0))

        self._inbound = SAPSimulatorInboundAdapter(
            plant=plant,
            company_code=company_code,
            latency_ms=latency_ms,
            failure_rate=failure_rate,
        )
        self._outbound = SAPSimulatorOutboundAdapter(
            plant=plant,
            company_code=company_code,
            latency_ms=latency_ms,
            failure_rate=failure_rate,
        )

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
