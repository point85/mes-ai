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


def _apply(target: Any, attr: str, value: Any) -> None:
    """Set attr on target only when value is a non-empty string/primitive."""
    if value is None or value == "":
        return
    setattr(target, attr, value)


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
        from mes.adapters.erp.oracle.config import oracle_settings
        from mes.config import settings

        # Propagate plugin manifest parameter values into the global settings
        # objects that the Oracle client/adapter read from.
        _apply(settings, "ERP_BASE_URL", config.get("base_url"))
        _apply(settings, "ERP_AUTH_TYPE", config.get("auth_type"))
        _apply(settings, "ERP_CLIENT_ID", config.get("client_id"))
        _apply(settings, "ERP_CLIENT_SECRET", config.get("client_secret"))
        _apply(settings, "ERP_TOKEN_URL", config.get("token_url"))
        _apply(oracle_settings, "ORACLE_ORGANIZATION_CODE", config.get("organization_code"))

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
