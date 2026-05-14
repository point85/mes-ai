"""
OPC-UA Equipment Adapter Plugin.

Wraps the OPC-UA equipment adapter as a plugin managed by the
plugin framework.

When ``state_tag`` and ``state_model_id`` are configured, the plugin
subscribes to OPC-UA data-change notifications on the tag and feeds
each value change into :class:`EquipmentStateEngine` so that equipment
state transitions are recorded and classified automatically.

The default integer→state-name mapping follows **OPC 40083** (PackML
Companion Specification).  If the PLC publishes state values as strings
instead of integers the raw string is forwarded directly to the engine.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from mes.framework.plugin.base import MESPlugin

logger = logging.getLogger("mes.plugins.opcua_equipment")

# OPC 40083 — PackML State Model integer → state-name mapping.
# Keys are the Int32 values published on the CurrentState node.
PACKML_INT_TO_STATE: dict[int, str] = {
    0: "Undefined",
    1: "Clearing",
    2: "Stopped",
    3: "Starting",
    4: "Idle",
    5: "Suspended",
    6: "Execute",
    7: "Stopping",
    8: "Aborting",
    9: "Aborted",
    10: "Holding",
    11: "Held",
    12: "Unholding",
    13: "Suspending",
    14: "Unsuspending",
    15: "Resetting",
    16: "Completing",
    17: "Complete",
}


class OPCUAEquipmentPlugin(MESPlugin):
    """Plugin wrapper for the OPC-UA equipment adapter."""

    def __init__(self) -> None:
        self._adapter: Any = None
        self._config: dict[str, Any] = {}
        self._subscription_handle: Any = None
        self._last_state: str | None = None

    async def initialize(self, config: dict[str, Any]) -> None:
        from mes.adapters.equipment.opcua.adapter import OPCUAEquipmentAdapter

        self._config = config
        self._adapter = OPCUAEquipmentAdapter()

    async def start(self) -> None:
        if self._adapter:
            await self._adapter.connect()

        state_tag = self._config.get("state_tag", "")
        state_model_id = self._config.get("state_model_id", "")
        equipment_id_tag = self._config.get("equipment_id_tag", "")

        if state_tag and state_model_id and equipment_id_tag:
            logger.info(
                "Subscribing to state tag '%s' using equipment id tag '%s' (model=%s)",
                state_tag,
                equipment_id_tag,
                state_model_id,
            )
            self._subscription_handle = await self._adapter.subscribe_tag(
                state_tag,
                self._on_state_change,
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
        """Async callback invoked by the OPC-UA subscription handler."""
        from mes.core.performance.engine import EquipmentStateEngine
        from mes.framework.db import async_session_factory

        raw = tag_value.value
        equipment_id_tag = self._config.get("equipment_id_tag", "")
        state_model_id = self._config.get("state_model_id", "")

        equipment_id = await self._adapter._client.read_tag(equipment_id_tag) if equipment_id_tag else None
        equipment_id_value = str(equipment_id[0]) if equipment_id and equipment_id[0] is not None else ""
        if not equipment_id_value:
            logger.warning(
                "Missing equipment identifier from tag '%s' while processing state change",
                equipment_id_tag,
            )
            return

        # Resolve state name from integer or string value
        if isinstance(raw, int):
            state_name = PACKML_INT_TO_STATE.get(raw)
            if state_name is None:
                logger.warning(
                    "Unknown PackML integer state %d from tag '%s'",
                    raw,
                    tag_value.tag_name,
                )
                return
        elif isinstance(raw, str):
            state_name = raw
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
            equipment_id_value,
            prev,
            state_name,
            raw,
        )

        try:
            async with async_session_factory() as session:
                await EquipmentStateEngine.transition_equipment(
                    session,
                    equipment_id=UUID(equipment_id_value),
                    new_state=state_name,
                    state_model_id=state_model_id,
                    notes=f"OPC-UA tag {tag_value.tag_name} value={raw}",
                )
                await session.commit()
        except Exception:
            logger.exception(
                "Failed to record state transition for equipment %s: %s -> %s",
                equipment_id_value,
                prev,
                state_name,
            )
