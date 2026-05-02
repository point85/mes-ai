"""
Modbus Equipment Simulator Plugin.

Starts an in-process Modbus/TCP server using pymodbus so the rest of the
MES framework (and the modbus-equipment plugin) can be tested without any
physical hardware.

Register layout:
  Holding registers (HR):
    0   — equipment state code (see PackML cycle below)
    1   — alarm code (0 = no alarm)
    2-3 — temperature as float32 big-endian (default 22.5 °C)
    100 — part counter

  Coils:
    0   — running flag (true when state == Execute)
    1   — alarm flag

  Discrete inputs (DI):
    0   — safety door closed (always true in simulator)

PackML state code mapping (matches the packml-availability plugin):
  0 → Stopped
  1 → Idle
  2 → Execute
  3 → Held
  4 → Aborted

Auto-cycle sequence (when auto_cycle=true):
  Stopped(0) → Idle(1) → Execute(2) → Idle(1) → repeat
  While in Execute the counter register is incremented by counter_increment
  every cycle_interval_sec.
"""

from __future__ import annotations

import asyncio
import logging
import struct
from typing import Any

from mes.framework.plugin.base import MESPlugin

logger = logging.getLogger("mes.plugins.modbus_equipment_simulator")

# PackML state code → name (kept in sync with packml-availability plugin)
_STATE_NAMES: dict[int, str] = {
    0: "Stopped",
    1: "Idle",
    2: "Execute",
    3: "Held",
    4: "Aborted",
}

# Auto-cycle: list of (state_code, label) steps
_CYCLE: list[tuple[int, str]] = [
    (0, "Stopped"),
    (1, "Idle"),
    (2, "Execute"),
    (1, "Idle"),
]


class ModbusEquipmentSimulatorPlugin(MESPlugin):
    """
    In-process Modbus/TCP server simulating a piece of plant equipment.

    The server accepts connections from the modbus-equipment plugin (or any
    Modbus/TCP master) and exposes a small register map suitable for
    end-to-end integration testing.
    """

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}
        self._server_task: asyncio.Task | None = None
        self._cycle_task: asyncio.Task | None = None
        # pymodbus data store — populated in start()
        self._context: Any = None

    # ── Lifecycle ────────────────────────────────────────────────

    async def initialize(self, config: dict[str, Any]) -> None:
        self._config = config
        logger.info(
            "Modbus simulator plugin initialised (host=%s, port=%s)",
            config.get("host", "0.0.0.0"),
            config.get("port", 5020),
        )

    async def start(self) -> None:
        from pymodbus.datastore import (
            ModbusSequentialDataBlock,
            ModbusServerContext,
            ModbusSlaveContext,
        )
        from pymodbus.server import StartAsyncTcpServer

        host = self._config.get("host", "0.0.0.0")
        port = int(self._config.get("port", 5020))
        unit_id = int(self._config.get("unit_id", 1))
        initial_state = int(self._config.get("initial_state_value", 1))
        initial_counter = int(self._config.get("initial_counter_value", 0))

        # ── Build data store ─────────────────────────────────────────

        # Coils (FC01): indices 0-7
        # 0: running flag, 1: alarm flag
        coil_block = ModbusSequentialDataBlock(0, [False] * 8)

        # Discrete inputs (FC02): indices 0-7
        # 0: safety door closed (always True)
        di_block = ModbusSequentialDataBlock(0, [True] + [False] * 7)

        # Holding registers (FC03/FC06/FC16): indices 0-200
        # 0:  state code, 1: alarm code, 2-3: temperature (float32_be), 100: counter
        hr_values = [0] * 201
        hr_values[0] = initial_state
        hr_values[1] = 0  # no alarm

        # Pack 22.5 as float32 big-endian into registers 2 and 3
        packed = struct.pack(">f", 22.5)
        hi, lo = struct.unpack(">HH", packed)
        hr_values[2] = hi
        hr_values[3] = lo
        hr_values[100] = initial_counter

        hr_block = ModbusSequentialDataBlock(0, hr_values)

        # Input registers (FC04): same layout as HR but read-only
        ir_block = ModbusSequentialDataBlock(0, hr_values[:])

        slave = ModbusSlaveContext(
            di=di_block,
            co=coil_block,
            hr=hr_block,
            ir=ir_block,
        )
        self._context = ModbusServerContext(slaves={unit_id: slave}, single=False)

        # ── Start server ─────────────────────────────────────────────

        logger.info("Starting Modbus simulator server on %s:%d (unit=%d)", host, port, unit_id)
        self._server_task = asyncio.create_task(
            StartAsyncTcpServer(
                context=self._context,
                address=(host, port),
            ),
            name="modbus-simulator-server",
        )

        # Give the server a moment to bind before returning
        await asyncio.sleep(0.2)

        # ── Auto-cycle ───────────────────────────────────────────────
        if self._config.get("auto_cycle", False):
            self._cycle_task = asyncio.create_task(
                self._auto_cycle(unit_id),
                name="modbus-simulator-cycle",
            )

    async def stop(self) -> None:
        if self._cycle_task is not None:
            self._cycle_task.cancel()
            self._cycle_task = None

        if self._server_task is not None:
            self._server_task.cancel()
            try:
                await self._server_task
            except (asyncio.CancelledError, Exception):
                pass
            self._server_task = None

        logger.info("Modbus simulator stopped")

    async def health_check(self) -> bool:
        return (
            self._server_task is not None
            and not self._server_task.done()
        )

    # ── Register access helpers ──────────────────────────────────

    def get_holding_register(self, unit_id: int, address: int) -> int:
        """Read a holding register value (for tests / diagnostic REST endpoint)."""
        if self._context is None:
            return 0
        slave = self._context[unit_id]
        return slave.getValues(3, address, count=1)[0]  # FC03 = 3

    def set_holding_register(self, unit_id: int, address: int, value: int) -> None:
        """Write a holding register value (used by auto-cycle and tests)."""
        if self._context is None:
            return
        slave = self._context[unit_id]
        slave.setValues(3, address, [value])
        # Mirror into input registers
        slave.setValues(4, address, [value])

    def set_coil(self, unit_id: int, address: int, value: bool) -> None:
        """Write a coil value."""
        if self._context is None:
            return
        slave = self._context[unit_id]
        slave.setValues(1, address, [value])

    # ── Auto-cycle loop ──────────────────────────────────────────

    async def _auto_cycle(self, unit_id: int) -> None:
        """Cycle through PackML states automatically."""
        interval = float(self._config.get("cycle_interval_sec", 10.0))
        counter_inc = int(self._config.get("counter_increment", 1))
        step_index = 0

        while True:
            try:
                state_code, state_name = _CYCLE[step_index % len(_CYCLE)]
                self.set_holding_register(unit_id, 0, state_code)

                # Update running coil
                self.set_coil(unit_id, 0, state_code == 2)  # coil 0 = running

                # Increment counter while executing
                if state_code == 2:
                    current = self.get_holding_register(unit_id, 100)
                    self.set_holding_register(unit_id, 100, current + counter_inc)

                logger.debug(
                    "Modbus simulator: state=%s (%d), counter=%d",
                    state_name,
                    state_code,
                    self.get_holding_register(unit_id, 100),
                )
                step_index += 1
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.warning("Modbus simulator cycle error: %s", exc)
                await asyncio.sleep(interval)
