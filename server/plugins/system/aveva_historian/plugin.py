"""
AVEVA Historian Equipment Adapter Plugin.

Wraps the AVEVA Historian adapter as a plugin managed by the
plugin framework.

Supports multiple equipment mappings per historian instance.
For each mapping that has ``state_tag_fqn`` and ``state_model_id``
configured, the plugin subscribes (via polling) to the state tag
and feeds value changes into :class:`EquipmentStateEngine` so that
equipment state transitions are recorded automatically.

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


class _EquipmentTracker:
    """Per-equipment state tracking for one mapping entry."""

    __slots__ = ("equipment_id", "state_tag_fqn", "state_model_id", "tag_prefix",
                 "subscription_handle", "last_state")

    def __init__(self, mapping: dict[str, Any]) -> None:
        self.equipment_id: str = mapping.get("equipment_id", "")
        self.state_tag_fqn: str = mapping.get("state_tag_fqn", "")
        self.state_model_id: str = mapping.get("state_model_id", "")
        self.tag_prefix: str = mapping.get("tag_prefix", "")
        self.subscription_handle: Any = None
        self.last_state: str | None = None


class AVEVAHistorianPlugin(MESPlugin):
    """Plugin wrapper for the AVEVA Historian equipment adapter."""

    def __init__(self) -> None:
        self._adapter: Any = None
        self._config: dict[str, Any] = {}
        self._trackers: list[_EquipmentTracker] = []

    async def initialize(self, config: dict[str, Any]) -> None:
        from mes.adapters.historian.aveva.adapter import AVEVAHistorianAdapter
        from mes.adapters.historian.aveva.config import (
            AVEVAHistorianSettings,
            EquipmentMapping,
        )

        self._config = config

        # Map plugin config keys → AVEVAHistorianSettings env-style keys
        settings_kwargs: dict[str, Any] = {}
        _MAP = {
            "base_url": "AVEVA_BASE_URL",
            "datasource": "AVEVA_DATASOURCE",
            "auth_mode": "AVEVA_AUTH_MODE",
            "username": "AVEVA_USERNAME",
            "password": "AVEVA_PASSWORD",
            "bearer_token": "AVEVA_BEARER_TOKEN",
            "verify_ssl": "AVEVA_VERIFY_SSL",
            "timeout_sec": "AVEVA_TIMEOUT_SEC",
            "poll_interval_sec": "AVEVA_POLL_INTERVAL_SEC",
        }
        for cfg_key, settings_key in _MAP.items():
            if cfg_key in config and config[cfg_key] is not None:
                settings_kwargs[settings_key] = config[cfg_key]

        # Build equipment mappings
        raw_mappings = config.get("equipment_mappings") or []
        if isinstance(raw_mappings, str):
            import json
            try:
                raw_mappings = json.loads(raw_mappings)
            except (json.JSONDecodeError, TypeError):
                raw_mappings = []

        mappings = [
            EquipmentMapping(**m) if isinstance(m, dict) else m
            for m in raw_mappings
        ]
        settings_kwargs["AVEVA_EQUIPMENT_MAPPINGS"] = mappings

        # Build trackers
        self._trackers = [
            _EquipmentTracker(m if isinstance(m, dict) else m.model_dump())
            for m in raw_mappings
        ]

        settings = AVEVAHistorianSettings(_env_file=None, **settings_kwargs)
        self._adapter = AVEVAHistorianAdapter(settings)

    async def start(self) -> None:
        if self._adapter:
            await self._adapter.connect()

        poll_sec = self._config.get("poll_interval_sec", 5)

        for tracker in self._trackers:
            if tracker.state_tag_fqn and tracker.state_model_id and tracker.equipment_id:
                logger.info(
                    "Subscribing to state tag '%s' for equipment %s (model=%s)",
                    tracker.state_tag_fqn,
                    tracker.equipment_id,
                    tracker.state_model_id,
                )
                tracker.subscription_handle = await self._adapter.subscribe_tag(
                    tracker.state_tag_fqn,
                    self._make_state_callback(tracker),
                    interval_ms=int(poll_sec * 1000),
                )

    async def stop(self) -> None:
        if self._adapter:
            for tracker in self._trackers:
                if tracker.subscription_handle:
                    await self._adapter.unsubscribe(tracker.subscription_handle)
                    tracker.subscription_handle = None
            await self._adapter.disconnect()

    async def health_check(self) -> bool:
        return await self._adapter.health_check() if self._adapter else False

    def get_adapter(self) -> Any:
        return self._adapter

    # ── State-change callback factory ────────────────────────────

    def _make_state_callback(self, tracker: _EquipmentTracker):
        """Return an async callback bound to a specific equipment tracker."""

        async def _on_state_change(tag_value: Any) -> None:
            from mes.core.performance.engine import EquipmentStateEngine
            from mes.framework.db import async_session_factory

            raw = tag_value.value

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
            if state_name == tracker.last_state:
                return

            prev = tracker.last_state
            tracker.last_state = state_name

            logger.info(
                "Equipment %s state change: %s -> %s (raw=%r)",
                tracker.equipment_id,
                prev,
                state_name,
                raw,
            )

            try:
                async with async_session_factory() as session:
                    await EquipmentStateEngine.transition_equipment(
                        session,
                        equipment_id=UUID(tracker.equipment_id),
                        new_state=state_name,
                        state_model_id=tracker.state_model_id,
                        notes=f"AVEVA Historian tag {tag_value.tag_name} value={raw}",
                    )
                    await session.commit()
            except Exception:
                logger.exception(
                    "Failed to record state transition for equipment %s: %s -> %s",
                    tracker.equipment_id,
                    prev,
                    state_name,
                )

        return _on_state_change
