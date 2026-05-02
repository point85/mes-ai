"""
Modbus TCP/RTU Equipment Adapter Plugin.

Wraps ModbusEquipmentAdapter as a plugin managed by the plugin framework.

If a state_tag, state_value_map, state_model_id, and equipment_id are
configured, the plugin subscribes to the state tag after connecting and
feeds value changes into EquipmentStateEngine so equipment availability
and OEE are tracked automatically.

Configuration example (CLI):

  python -m mes.cli plugin install modbus-equipment \\
    --param host=192.168.1.10 \\
    --param port=502 \\
    --param unit_id=1 \\
    --param tag_map='{"status":{"type":"coil","address":0},"counter":{"type":"hr","address":100}}' \\
    --param state_tag=status \\
    --param state_value_map='{"0":"Stopped","1":"Idle","2":"Execute","3":"Faulted"}' \\
    --param state_model_id=packml \\
    --param equipment_id=<uuid>

  python -m mes.cli plugin enable modbus-equipment
"""

from __future__ import annotations

import logging
from typing import Any

from mes.framework.plugin.base import MESPlugin

logger = logging.getLogger("mes.plugins.modbus_equipment")


class ModbusEquipmentPlugin(MESPlugin):
    """Plugin wrapper for the Modbus TCP/RTU equipment adapter."""

    def __init__(self) -> None:
        self._adapter: Any = None
        self._config: dict[str, Any] = {}
        self._state_subscription: Any = None

    # ── Lifecycle ────────────────────────────────────────────────

    async def initialize(self, config: dict[str, Any]) -> None:
        from mes.adapters.equipment.modbus.adapter import ModbusEquipmentAdapter
        from mes.adapters.equipment.modbus.config import ModbusEquipmentSettings

        self._config = config

        # Map plugin config keys → settings env-var names
        _KEY_MAP = {
            "mode":              "MODBUS_MODE",
            "host":              "MODBUS_HOST",
            "port":              "MODBUS_PORT",
            "serial_port":       "MODBUS_SERIAL_PORT",
            "baudrate":          "MODBUS_BAUDRATE",
            "bytesize":          "MODBUS_BYTESIZE",
            "parity":            "MODBUS_PARITY",
            "stopbits":          "MODBUS_STOPBITS",
            "unit_id":           "MODBUS_UNIT_ID",
            "timeout":           "MODBUS_TIMEOUT",
            "retries":           "MODBUS_RETRIES",
            "poll_interval_sec": "MODBUS_POLL_INTERVAL_SEC",
            "tag_map":           "MODBUS_TAG_MAP",
            "state_tag":         "MODBUS_STATE_TAG",
            "state_value_map":   "MODBUS_STATE_VALUE_MAP",
            "state_model_id":    "MODBUS_STATE_MODEL_ID",
            "equipment_id":      "MODBUS_EQUIPMENT_ID",
        }

        kwargs: dict[str, Any] = {}
        for cfg_key, settings_key in _KEY_MAP.items():
            if config.get(cfg_key) is not None:
                kwargs[settings_key] = config[cfg_key]

        settings = ModbusEquipmentSettings(_env_file=None, **kwargs)
        self._adapter = ModbusEquipmentAdapter(settings)
        logger.info("Modbus equipment plugin initialised (mode=%s, host=%s, port=%s)",
                    settings.MODBUS_MODE.value, settings.MODBUS_HOST, settings.MODBUS_PORT)

    async def start(self) -> None:
        if self._adapter is None:
            return

        try:
            await self._adapter.connect()
        except Exception as exc:  # noqa: BLE001
            # Device may not be reachable yet; pymodbus will auto-reconnect.
            logger.warning("Modbus: initial connection failed (%s) — will retry automatically", exc)

        # Subscribe to state tag if configured
        state_tag = self._config.get("state_tag", "")
        state_model_id = self._config.get("state_model_id", "")
        equipment_id = self._config.get("equipment_id", "")
        poll_sec = float(self._config.get("poll_interval_sec", 1.0))

        if state_tag and state_model_id and equipment_id:
            logger.info(
                "Modbus: subscribing to state tag '%s' for equipment %s (model=%s)",
                state_tag, equipment_id, state_model_id,
            )
            self._state_subscription = await self._adapter.subscribe_tag(
                state_tag,
                self._make_state_callback(equipment_id, state_model_id),
                interval_ms=int(poll_sec * 1000),
            )

    async def stop(self) -> None:
        if self._adapter is None:
            return

        if self._state_subscription is not None:
            await self._adapter.unsubscribe(self._state_subscription)
            self._state_subscription = None

        await self._adapter.disconnect()

    async def health_check(self) -> bool:
        return await self._adapter.health_check() if self._adapter else False

    def get_adapter(self) -> Any:
        """Return the underlying ModbusEquipmentAdapter (used by tests and the REST diagnostic endpoint)."""
        return self._adapter

    # ── State change callback ────────────────────────────────────

    def _make_state_callback(self, equipment_id: str, state_model_id: str):
        """Return an async callback that feeds Modbus state changes into EquipmentStateEngine."""

        # Track the last published state to suppress duplicate transitions
        last_state: list[str | None] = [None]

        async def _on_state_change(tag_value: Any) -> None:
            from mes.core.performance.engine import EquipmentStateEngine
            from mes.framework.db import async_session_factory

            raw = tag_value.value

            # The tag value is already decoded by the adapter (bool/int/float)
            if isinstance(raw, bool):
                state_name = str(int(raw))
            elif isinstance(raw, float):
                state_name = str(int(raw))
            else:
                state_name = str(raw)

            # Look up state name in state_value_map (already applied by adapter's
            # get_equipment_state, but subscribe_tag gives raw TagValue)
            state_value_map = self._adapter._state_value_map if self._adapter else {}
            resolved = state_value_map.get(state_name, state_name)

            if resolved == last_state[0]:
                return  # No transition — skip DB write
            last_state[0] = resolved

            logger.debug("Modbus state change: equipment=%s state=%s", equipment_id, resolved)
            try:
                async with async_session_factory() as session:
                    from uuid import UUID
                    await EquipmentStateEngine.record_state_transition(
                        session,
                        equipment_id=UUID(equipment_id),
                        state_model_id=state_model_id,
                        new_state=resolved,
                    )
                    await session.commit()
            except Exception as exc:
                logger.warning(
                    "Modbus: failed to record state transition for equipment %s: %s",
                    equipment_id, exc,
                )

        return _on_state_change
