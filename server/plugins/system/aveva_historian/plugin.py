"""
AVEVA Historian Equipment Adapter Plugin.

Wraps the AVEVA Historian adapter as a plugin managed by the
plugin framework.

When ``state_tag_fqn`` and ``state_model_id`` are configured, the
plugin subscribes (via polling) to the state tag and feeds each
value change into :class:`EquipmentStateEngine` so that equipment
state transitions are recorded and classified automatically.

The Historian REST API is read-only for process data — no push
notifications or WebSocket support. All "subscriptions" are
implemented as periodic HTTP polls.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from mes.framework.plugin.base import MESPlugin

logger = logging.getLogger("mes.plugins.aveva_historian")


class AVEVAHistorianPlugin(MESPlugin):
    """Plugin wrapper for the AVEVA Historian equipment adapter."""

    def __init__(self) -> None:
        self._adapter: Any = None
        self._config: dict[str, Any] = {}
        self._subscription_handle: Any = None
        self._last_state: str | None = None

    async def initialize(self, config: dict[str, Any]) -> None:
        from mes.adapters.historian.aveva.adapter import AVEVAHistorianAdapter
        from mes.adapters.historian.aveva.config import AVEVAHistorianSettings

        self._config = config

        # Map plugin config keys → AVEVAHistorianSettings env-style keys
        settings_kwargs: dict[str, Any] = {}
        _MAP = {
            "base_url": "AVEVA_BASE_URL",
            "datasource": "AVEVA_DATASOURCE",
            "equipment_id": "AVEVA_EQUIPMENT_ID",
            "auth_mode": "AVEVA_AUTH_MODE",
            "username": "AVEVA_USERNAME",
            "password": "AVEVA_PASSWORD",
            "bearer_token": "AVEVA_BEARER_TOKEN",
            "verify_ssl": "AVEVA_VERIFY_SSL",
            "timeout_sec": "AVEVA_TIMEOUT_SEC",
            "tag_prefix": "AVEVA_TAG_PREFIX",
            "state_tag_fqn": "AVEVA_STATE_TAG_FQN",
            "state_model_id": "AVEVA_STATE_MODEL_ID",
            "poll_interval_sec": "AVEVA_POLL_INTERVAL_SEC",
        }
        for cfg_key, settings_key in _MAP.items():
            if cfg_key in config and config[cfg_key] is not None:
                settings_kwargs[settings_key] = config[cfg_key]

        settings = AVEVAHistorianSettings(**settings_kwargs)
        self._adapter = AVEVAHistorianAdapter(settings)

    async def start(self) -> None:
        if self._adapter:
            await self._adapter.connect()

        state_tag_fqn = self._config.get("state_tag_fqn", "")
        state_model_id = self._config.get("state_model_id", "")
        equipment_id = self._config.get("equipment_id", "")

        if state_tag_fqn and state_model_id and equipment_id:
            logger.info(
                "Subscribing to state tag '%s' for equipment %s (model=%s)",
                state_tag_fqn,
                equipment_id,
                state_model_id,
            )
            poll_sec = self._config.get("poll_interval_sec", 5)
            self._subscription_handle = await self._adapter.subscribe_tag(
                state_tag_fqn,
                self._on_state_change,
                interval_ms=int(poll_sec * 1000),
            )

    async def stop(self) -> None:
        if self._adapter:
            if self._subscription_handle:
                await self._adapter.unsubscribe(self._subscription_handle)
                self._subscription_handle = None
            await self._adapter.disconnect()

    async def health_check(self) -> bool:
        return await self._adapter.health_check() if self._adapter else False

    def get_adapter(self) -> Any:
        return self._adapter

    # ── State-change callback ────────────────────────────────────

    async def _on_state_change(self, tag_value: Any) -> None:
        """Async callback invoked by the polling subscription."""
        from mes.core.performance.engine import EquipmentStateEngine
        from mes.framework.db import async_session_factory

        raw = tag_value.value
        equipment_id = self._config.get("equipment_id", "")
        state_model_id = self._config.get("state_model_id", "")

        # Resolve state name
        if isinstance(raw, str):
            state_name = raw
        elif isinstance(raw, (int, float)):
            state_name = str(raw)
        else:
            logger.warning(
                "Unexpected state value type %s from tag '%s': %r",
                type(raw).__name__,
                tag_value.tag_name,
                raw,
            )
            return

        # Skip duplicate transitions
        if state_name == self._last_state:
            return

        prev = self._last_state
        self._last_state = state_name

        logger.info(
            "Equipment %s state change: %s -> %s (raw=%r)",
            equipment_id,
            prev,
            state_name,
            raw,
        )

        try:
            async with async_session_factory() as session:
                await EquipmentStateEngine.transition_equipment(
                    session,
                    equipment_id=UUID(equipment_id),
                    new_state=state_name,
                    state_model_id=state_model_id,
                    notes=f"AVEVA Historian tag {tag_value.tag_name} value={raw}",
                )
                await session.commit()
        except Exception:
            logger.exception(
                "Failed to record state transition for equipment %s: %s -> %s",
                equipment_id,
                prev,
                state_name,
            )
