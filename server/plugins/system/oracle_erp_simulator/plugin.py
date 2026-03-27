"""
Oracle Cloud ERP Simulator Plugin.

Wraps OracleSimulatorInboundAdapter and OracleSimulatorOutboundAdapter as a
unified plugin managed by the MES plugin framework.

Unlike the real oracle_cloud_erp plugin (which talks to a live Oracle Fusion
instance over REST), this plugin generates realistic Oracle-format data in
memory and runs it through the OracleTransformLayer — exercising the full
inbound/outbound data pipeline without any external dependency.
"""

from __future__ import annotations

from typing import Any

from mes.framework.plugin import MESPlugin


class OracleERPSimulatorPlugin(MESPlugin):
    """Plugin wrapper for the Oracle ERP simulator adapter pair."""

    def __init__(self) -> None:
        self._inbound: Any = None
        self._outbound: Any = None

    async def initialize(self, config: dict[str, Any]) -> None:
        from .simulator import OracleSimulatorInboundAdapter, OracleSimulatorOutboundAdapter

        organization_code = str(config.get("organization_code", "ORG_MAIN"))
        business_unit = str(config.get("business_unit", "BU_MANUFACTURING"))
        latency_ms = int(config.get("latency_ms", 0))
        failure_rate = float(config.get("failure_rate", 0.0))

        self._inbound = OracleSimulatorInboundAdapter(
            organization_code=organization_code,
            business_unit=business_unit,
            latency_ms=latency_ms,
            failure_rate=failure_rate,
        )
        self._outbound = OracleSimulatorOutboundAdapter(
            organization_code=organization_code,
            business_unit=business_unit,
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
