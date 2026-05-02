"""
Modbus TCP/RTU Equipment Adapter.

Implements the EquipmentAdapter interface using pymodbus (>=3.6) for
Modbus/TCP and Modbus RTU transports.

Register descriptor schema (entries in the tag_map config):
  type     - "coil" | "di" | "hr" | "ir"
  address  - 0-based Modbus address
  count    - registers to read (1 for int/uint, 2 for float32)
  decode   - "uint16" | "int16" | "float32_be" | "float32_le"
  scale    - raw value multiplier (default 1.0)
  offset   - offset added after scaling (default 0.0)

Tag subscriptions are poll-based: an asyncio task reads the tag at
the configured interval and invokes the callback when the value
changes (or always, depending on the callback contract).

State tracking:
  If state_tag is configured, get_equipment_state() reads that tag,
  looks up the raw value in state_value_map, and returns a canonical
  EquipmentState.  The plugin layer feeds state changes into
  EquipmentStateEngine for availability/OEE tracking.
"""

from __future__ import annotations

import asyncio
import logging
import struct
from collections.abc import Callable
from typing import Any

from mes.adapters.equipment.dtos import EquipmentState, SubscriptionHandle, TagInfo, TagValue
from mes.adapters.equipment.exceptions import (
    CommunicationTimeoutError,
    EquipmentConnectionError,
    TagNotFoundError,
)
from mes.adapters.equipment.interfaces import EquipmentAdapter

from .config import ModbusEquipmentSettings, ModbusMode

logger = logging.getLogger("mes.adapters.equipment.modbus")

# Default state → dispatch category mapping for raw string state names
_DEFAULT_DISPATCH: dict[str, str] = {
    "execute": "busy",
    "running": "busy",
    "starting": "busy",
    "completing": "busy",
    "idle": "available",
    "complete": "available",
    "stopped": "unavailable_planned",
    "stopping": "unavailable_planned",
    "suspended": "unavailable_planned",
    "suspending": "unavailable_planned",
    "held": "unavailable_unplanned",
    "holding": "unavailable_unplanned",
    "faulted": "unavailable_unplanned",
    "fault": "unavailable_unplanned",
    "aborted": "unavailable_unplanned",
    "aborting": "unavailable_unplanned",
    "error": "unavailable_unplanned",
}

_DEFAULT_OEE: dict[str, str] = {
    "execute": "uptime_value_add",
    "running": "uptime_value_add",
    "starting": "uptime_value_add",
    "completing": "uptime_value_add",
    "idle": "uptime_non_value",
    "complete": "uptime_non_value",
    "stopped": "downtime_planned",
    "stopping": "downtime_planned",
    "suspended": "downtime_planned",
    "suspending": "downtime_planned",
    "held": "downtime_unplanned",
    "holding": "downtime_unplanned",
    "faulted": "downtime_unplanned",
    "fault": "downtime_unplanned",
    "aborted": "downtime_unplanned",
    "aborting": "downtime_unplanned",
    "error": "downtime_unplanned",
}


class _ActiveSubscription:
    """Tracks a running poll-loop task for one tag subscription."""

    __slots__ = ("handle", "task")

    def __init__(self, handle: SubscriptionHandle, task: asyncio.Task) -> None:
        self.handle = handle
        self.task = task


def _decode_registers(registers: list[int], descriptor: dict) -> Any:
    """
    Decode one or more register values according to the descriptor.

    Supports:
      decode="uint16"     (default) — unsigned 16-bit integer
      decode="int16"      — signed 16-bit integer
      decode="float32_be" — 32-bit float, big-endian word order
      decode="float32_le" — 32-bit float, little-endian word order

    After decoding, applies scale and offset:
      result = raw * scale + offset
    """
    decode = descriptor.get("decode", "uint16")
    scale = float(descriptor.get("scale", 1.0))
    offset = float(descriptor.get("offset", 0.0))

    if decode == "int16":
        raw = struct.unpack(">h", struct.pack(">H", registers[0]))[0]
    elif decode == "float32_be" and len(registers) >= 2:
        raw = struct.unpack(">f", struct.pack(">HH", registers[0], registers[1]))[0]
    elif decode == "float32_le" and len(registers) >= 2:
        raw = struct.unpack(">f", struct.pack(">HH", registers[1], registers[0]))[0]
    else:
        raw = registers[0]  # uint16

    return raw * scale + offset if (scale != 1.0 or offset != 0.0) else raw


class ModbusEquipmentAdapter(EquipmentAdapter):
    """
    Modbus TCP/RTU equipment adapter.

    Reads and writes Modbus coils, discrete inputs, holding registers,
    and input registers.  Subscriptions are poll-based.

    Usage::

        settings = ModbusEquipmentSettings(
            MODBUS_HOST="192.168.1.10",
            MODBUS_TAG_MAP='{"status": {"type": "coil", "address": 0}, '
                           '"counter": {"type": "hr", "address": 100}}',
        )
        adapter = ModbusEquipmentAdapter(settings)
        await adapter.connect()
        tv = await adapter.read_tag("counter")
        await adapter.disconnect()
    """

    def __init__(self, settings: ModbusEquipmentSettings | None = None) -> None:
        self._settings = settings or ModbusEquipmentSettings()
        self._client: Any = None
        self._tag_map: dict[str, dict] = self._settings.get_tag_map()
        self._state_value_map: dict[str, str] = self._settings.get_state_value_map()
        self._subscriptions: dict[str, _ActiveSubscription] = {}

    # ── Lifecycle ────────────────────────────────────────────────

    async def connect(self) -> None:
        """Establish Modbus connection."""
        try:
            if self._settings.MODBUS_MODE == ModbusMode.TCP:
                from pymodbus.client import AsyncModbusTcpClient
                self._client = AsyncModbusTcpClient(
                    host=self._settings.MODBUS_HOST,
                    port=self._settings.MODBUS_PORT,
                    timeout=self._settings.MODBUS_TIMEOUT,
                    retries=self._settings.MODBUS_RETRIES,
                    retry_on_empty=True,
                )
            else:
                from pymodbus.client import AsyncModbusSerialClient
                self._client = AsyncModbusSerialClient(
                    port=self._settings.MODBUS_SERIAL_PORT,
                    baudrate=self._settings.MODBUS_BAUDRATE,
                    bytesize=self._settings.MODBUS_BYTESIZE,
                    parity=self._settings.MODBUS_PARITY,
                    stopbits=self._settings.MODBUS_STOPBITS,
                    timeout=self._settings.MODBUS_TIMEOUT,
                )

            connected = await self._client.connect()
            if not connected:
                raise EquipmentConnectionError(
                    f"Modbus {self._settings.MODBUS_MODE.value} connect failed "
                    f"({self._settings.MODBUS_HOST}:{self._settings.MODBUS_PORT})"
                )
            logger.info(
                "Modbus %s connected to %s:%d (unit=%d)",
                self._settings.MODBUS_MODE.value,
                self._settings.MODBUS_HOST,
                self._settings.MODBUS_PORT,
                self._settings.MODBUS_UNIT_ID,
            )
        except EquipmentConnectionError:
            raise
        except Exception as exc:
            raise EquipmentConnectionError(str(exc)) from exc

    async def disconnect(self) -> None:
        """Cancel all subscriptions and close the Modbus connection."""
        for sub in list(self._subscriptions.values()):
            sub.task.cancel()
        self._subscriptions.clear()

        if self._client is not None:
            self._client.close()
            self._client = None
        logger.info("Modbus adapter disconnected")

    async def health_check(self) -> bool:
        """Return True if the client is connected."""
        if self._client is None:
            return False
        return bool(getattr(self._client, "connected", False))

    # ── Tag I/O ──────────────────────────────────────────────────

    async def read_tag(self, tag_name: str) -> TagValue:
        """Read the current value of a named tag."""
        descriptor = self._tag_map.get(tag_name)
        if descriptor is None:
            raise TagNotFoundError(tag_name)

        value = await self._read_descriptor(descriptor)
        return TagValue(tag_name=tag_name, value=value, quality="good")

    async def write_tag(self, tag_name: str, value: Any) -> None:
        """Write a value to a named tag."""
        descriptor = self._tag_map.get(tag_name)
        if descriptor is None:
            raise TagNotFoundError(tag_name)

        reg_type = descriptor.get("type", "hr")
        address = int(descriptor["address"])
        unit = self._settings.MODBUS_UNIT_ID

        self._require_client()
        try:
            if reg_type == "coil":
                result = await self._client.write_coil(address, bool(value), slave=unit)
            elif reg_type == "hr":
                if isinstance(value, float):
                    # Write float32 as two holding registers
                    packed = struct.pack(">f", value)
                    hi, lo = struct.unpack(">HH", packed)
                    result = await self._client.write_registers(address, [hi, lo], slave=unit)
                else:
                    result = await self._client.write_register(address, int(value), slave=unit)
            elif reg_type in ("di", "ir"):
                raise ValueError(f"Tag '{tag_name}' is read-only ({reg_type})")
            else:
                raise ValueError(f"Unknown register type '{reg_type}' for tag '{tag_name}'")

            if result.isError():
                raise CommunicationTimeoutError(f"Modbus write error for tag '{tag_name}': {result}")

        except (EquipmentConnectionError, CommunicationTimeoutError, ValueError):
            raise
        except Exception as exc:
            raise CommunicationTimeoutError(str(exc)) from exc

    async def subscribe_tag(
        self,
        tag_name: str,
        callback: Callable[[TagValue], Any],
        interval_ms: int = 1000,
    ) -> SubscriptionHandle:
        """
        Start a poll loop that reads the tag at `interval_ms` intervals
        and invokes `callback` on every read (regardless of value change).
        """
        if tag_name not in self._tag_map:
            raise TagNotFoundError(tag_name)

        handle = SubscriptionHandle(tag_name=tag_name)
        task = asyncio.create_task(
            self._poll_loop(tag_name, callback, interval_ms / 1000.0),
            name=f"modbus-poll-{tag_name}",
        )
        self._subscriptions[handle.handle_id] = _ActiveSubscription(handle, task)
        logger.debug("Modbus: subscribed to tag '%s' @ %d ms", tag_name, interval_ms)
        return handle

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        """Cancel a tag poll loop."""
        sub = self._subscriptions.pop(handle.handle_id, None)
        if sub:
            sub.task.cancel()
            handle.active = False

    async def get_equipment_state(self) -> EquipmentState:
        """
        Read the configured state tag and map it to a canonical EquipmentState.

        If no state_tag is configured, returns a generic 'unknown' state.
        """
        equip_id = self._settings.MODBUS_EQUIPMENT_ID
        state_tag = self._settings.MODBUS_STATE_TAG

        if not state_tag:
            return EquipmentState(
                equipment_id=equip_id,
                state="unknown",
                dispatch_category="available",
                oee_bucket="uptime_non_value",
            )

        tv = await self.read_tag(state_tag)
        raw_str = str(int(tv.value))
        state_name = self._state_value_map.get(raw_str, raw_str)
        state_lower = state_name.lower()

        return EquipmentState(
            equipment_id=equip_id,
            state=state_name,
            dispatch_category=_DEFAULT_DISPATCH.get(state_lower, "available"),
            oee_bucket=_DEFAULT_OEE.get(state_lower, "uptime_non_value"),
        )

    # ── Tag browsing ─────────────────────────────────────────────

    async def browse_tags(self) -> list[TagInfo]:
        """Return TagInfo for every entry in the configured tag_map."""
        results = []
        for tag_name, desc in self._tag_map.items():
            reg_type = desc.get("type", "hr")
            access = "readwrite" if reg_type in ("coil", "hr") else "read"
            decode = desc.get("decode", "uint16")
            if decode.startswith("float"):
                data_type = "float"
            elif reg_type == "coil" or reg_type == "di":
                data_type = "bool"
            else:
                data_type = "int"
            results.append(TagInfo(tag_name=tag_name, data_type=data_type, access=access))
        return results

    # ── Internal helpers ─────────────────────────────────────────

    def _require_client(self) -> None:
        if self._client is None or not getattr(self._client, "connected", False):
            raise EquipmentConnectionError("Modbus client is not connected")

    async def _read_descriptor(self, descriptor: dict) -> Any:
        """Execute the appropriate Modbus read for a register descriptor."""
        self._require_client()
        reg_type = descriptor.get("type", "hr")
        address = int(descriptor["address"])
        count = int(descriptor.get("count", 1))
        unit = self._settings.MODBUS_UNIT_ID

        try:
            if reg_type == "coil":
                result = await self._client.read_coils(address, count, slave=unit)
                if result.isError():
                    raise CommunicationTimeoutError(f"Modbus read_coils error: {result}")
                return bool(result.bits[0])

            elif reg_type == "di":
                result = await self._client.read_discrete_inputs(address, count, slave=unit)
                if result.isError():
                    raise CommunicationTimeoutError(f"Modbus read_discrete_inputs error: {result}")
                return bool(result.bits[0])

            elif reg_type == "hr":
                result = await self._client.read_holding_registers(address, count, slave=unit)
                if result.isError():
                    raise CommunicationTimeoutError(f"Modbus read_holding_registers error: {result}")
                return _decode_registers(result.registers, descriptor)

            elif reg_type == "ir":
                result = await self._client.read_input_registers(address, count, slave=unit)
                if result.isError():
                    raise CommunicationTimeoutError(f"Modbus read_input_registers error: {result}")
                return _decode_registers(result.registers, descriptor)

            else:
                raise TagNotFoundError(f"Unknown register type '{reg_type}'")

        except (CommunicationTimeoutError, TagNotFoundError, EquipmentConnectionError):
            raise
        except asyncio.TimeoutError as exc:
            raise CommunicationTimeoutError("Modbus read timed out") from exc
        except Exception as exc:
            raise CommunicationTimeoutError(str(exc)) from exc

    async def _poll_loop(
        self,
        tag_name: str,
        callback: Callable[[TagValue], Any],
        interval_sec: float,
    ) -> None:
        """Background task: poll one tag and invoke the callback."""
        while True:
            try:
                tv = await self.read_tag(tag_name)
                result = callback(tv)
                if asyncio.iscoroutine(result):
                    await result
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.warning("Modbus poll error for tag '%s': %s", tag_name, exc)
            await asyncio.sleep(interval_sec)
