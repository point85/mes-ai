"""
Mock ERP Adapter Plugin.

Wraps the built-in MockERPInboundAdapter and MockERPOutboundAdapter
as a unified plugin managed by the plugin framework.
"""

from __future__ import annotations

from typing import Any

from mes.adapters.erp.mock_adapter import (
    MockERPInboundAdapter,
    MockERPOutboundAdapter,
)
from mes.framework.plugin import MESPlugin


class MockERPPlugin(MESPlugin):
    """Plugin wrapper for the mock ERP adapter pair."""

    def __init__(self) -> None:
        self._inbound: MockERPInboundAdapter | None = None
        self._outbound: MockERPOutboundAdapter | None = None

    async def initialize(self, config: dict[str, Any]) -> None:
        latency_ms = int(config.get("latency_ms", 0))
        failure_rate = float(config.get("failure_rate", 0.0))
        self._inbound = MockERPInboundAdapter(
            latency_ms=latency_ms,
            failure_rate=failure_rate,
        )
        self._outbound = MockERPOutboundAdapter(
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
