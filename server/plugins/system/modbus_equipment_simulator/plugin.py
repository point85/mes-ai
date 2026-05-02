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

# pymodbus 3.6 function codes used with async_getValues / async_setValues
_FC_COIL = 1   # Coils (read/write)
_FC_DI   = 2   # Discrete inputs (read-only)
_FC_HR   = 3   # Holding registers (read/write)
_FC_IR   = 4   # Input registers (read-only)

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
        self._server: Any = None   # ModbusTcpServer — set in start()
        self._unit_id: int = 1

    # ── Lifecycle ────────────────────────────────────────────────

    async def initialize(self, config: dict[str, Any]) -> None:
        self._config = config
        logger.info(
            "Modbus simulator plugin initialised (host=%s, port=%s)",
            config.get("host", "0.0.0.0"),
            config.get("port", 5020),
        )

    async def start(self) -> None:
        from pymodbus.server import ModbusTcpServer
        from pymodbus.simulator.simdata import DataType, SimData
        from pymodbus.simulator.simdevice import SimDevice

        host = self._config.get("host", "0.0.0.0")
        port = int(self._config.get("port", 5020))
        unit_id = int(self._config.get("unit_id", 1))
        initial_state = int(self._config.get("initial_state_value", 1))
        initial_counter = int(self._config.get("initial_counter_value", 0))
        self._unit_id = unit_id

        # ── Build initial register values ────────────────────────────────────
        # HR array (0-based index). SimData uses Modbus 1-based addressing,
        # so SimData(address=1) maps index 0 → Modbus HR 1, etc.
        hr_vals = [0] * 201
        hr_vals[0] = initial_state        # HR[0]: equipment state code
        hr_vals[1] = 0                    # HR[1]: alarm code (0 = no alarm)
        # HR[2-3]: temperature 22.5 °C as float32 big-endian
        packed = struct.pack(">f", 22.5)
        hi, lo = struct.unpack(">HH", packed)
        hr_vals[2] = hi
        hr_vals[3] = lo
        hr_vals[100] = initial_counter    # HR[100]: part counter

        # ── Build SimDevice with separate function-code blocks ───────────────
        # Tuple order: (coils, discrete_inputs, holding_registers, input_registers)
        # SimData address is 1-based Modbus address.
        coils  = SimData(1, count=8,   datatype=DataType.BITS,      values=[False] * 8)
        dis    = SimData(1, count=8,   datatype=DataType.BITS,      values=[True] + [False] * 7)
        hrs    = SimData(1, count=201, datatype=DataType.REGISTERS, values=hr_vals)
        irs    = SimData(1, count=201, datatype=DataType.REGISTERS, values=hr_vals[:])
        device = SimDevice(id=unit_id, simdata=([coils], [dis], [hrs], [irs]))

        # ── Start server ─────────────────────────────────────────────────────
        self._server = ModbusTcpServer(context=device, address=(host, port))

        logger.info(
            "Starting Modbus simulator server on %s:%d (unit=%d)", host, port, unit_id
        )
        self._server_task = asyncio.create_task(
            self._server.serve_forever(),
            name="modbus-simulator-server",
        )

        # Give the server a moment to bind before returning
        await asyncio.sleep(0.2)

        # ── Auto-cycle ───────────────────────────────────────────────────────
        auto_cycle = self._config.get("auto_cycle", False)
        if isinstance(auto_cycle, str):
            auto_cycle = auto_cycle.lower() in ("true", "1", "yes")

        if auto_cycle:
            self._cycle_task = asyncio.create_task(
                self._auto_cycle(unit_id),
                name="modbus-simulator-cycle",
            )
            logger.info(
                "Modbus simulator auto-cycle enabled (interval=%ss)",
                self._config.get("cycle_interval_sec", 10.0),
            )

    async def stop(self) -> None:
        if self._cycle_task is not None:
            self._cycle_task.cancel()
            self._cycle_task = None

        if self._server is not None:
            await self._server.shutdown()
            self._server = None

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

    async def get_holding_register(self, unit_id: int, address: int) -> int:
        """Read a holding register value (0-based address, for tests/diagnostics)."""
        if self._server is None:
            return 0
        vals = await self._server.async_getValues(
            device_id=unit_id, func_code=_FC_HR, address=address + 1, count=1
        )
        return int(vals[0]) if vals else 0

    async def set_holding_register(self, unit_id: int, address: int, value: int) -> None:
        """Write a holding register (0-based address). Mirrors the write into IR."""
        if self._server is None:
            return
        addr1 = address + 1  # convert to 1-based Modbus address
        await self._server.async_setValues(
            device_id=unit_id, func_code=_FC_HR, address=addr1, values=[value]
        )
        # Mirror into input registers so FC04 reads are consistent
        await self._server.async_setValues(
            device_id=unit_id, func_code=_FC_IR, address=addr1, values=[value]
        )

    async def set_coil(self, unit_id: int, address: int, value: bool) -> None:
        """Write a coil (0-based address)."""
        if self._server is None:
            return
        await self._server.async_setValues(
            device_id=unit_id, func_code=_FC_COIL, address=address + 1, values=[value]
        )

    # ── Auto-cycle loop ──────────────────────────────────────────

    async def _auto_cycle(self, unit_id: int) -> None:
        """Cycle through PackML states automatically."""
        interval = float(self._config.get("cycle_interval_sec", 10.0))
        counter_inc = int(self._config.get("counter_increment", 1))
        step_index = 0

        while True:
            try:
                state_code, state_name = _CYCLE[step_index % len(_CYCLE)]
                await self.set_holding_register(unit_id, 0, state_code)

                # Update running coil (coil 0 = running)
                await self.set_coil(unit_id, 0, state_code == 2)

                # Increment counter while in Execute
                if state_code == 2:
                    current = await self.get_holding_register(unit_id, 100)
                    await self.set_holding_register(unit_id, 100, current + counter_inc)

                counter = await self.get_holding_register(unit_id, 100)
                logger.debug(
                    "Modbus simulator: state=%s (%d), counter=%d",
                    state_name,
                    state_code,
                    counter,
                )
                step_index += 1
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.warning("Modbus simulator cycle error: %s", exc)
                await asyncio.sleep(interval)
