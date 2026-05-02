"""
Modbus Equipment Adapter: Configuration via pydantic-settings.

Supports both Modbus/TCP (host + port) and Modbus RTU (serial port + baud rate).

The tag_map is a JSON string mapping logical tag names to Modbus register
descriptors:

  {
    "status":      {"type": "coil",  "address": 0},
    "alarm":       {"type": "di",    "address": 0},
    "setpoint":    {"type": "hr",    "address": 100},
    "temperature": {"type": "ir",    "address": 200, "count": 2, "decode": "float32_be"},
    "counter":     {"type": "hr",    "address": 300, "scale": 0.1, "offset": 0.0}
  }

Register descriptor fields:
  type     - "coil" | "di" | "hr" | "ir"
  address  - 0-based Modbus register/coil address
  count    - number of registers to read (default 1; use 2 for float32)
  decode   - decoding hint: "uint16" (default) | "int16" | "float32_be" | "float32_le"
  scale    - multiply raw value by this factor (default 1.0)
  offset   - add this to scaled value (default 0.0)

The state_value_map is a JSON string mapping raw register values (as strings)
to canonical state names understood by the configured state model:

  {"0": "Stopped", "1": "Idle", "2": "Execute", "3": "Held", "4": "Aborted"}
"""

from __future__ import annotations

import json
from enum import Enum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ModbusMode(str, Enum):
    """Modbus transport mode."""

    TCP = "tcp"
    RTU = "rtu"


class ModbusEquipmentSettings(BaseSettings):
    """Configuration for the Modbus equipment adapter."""

    # ── Transport selection ──────────────────────────────────────

    MODBUS_MODE: ModbusMode = Field(ModbusMode.TCP, description="tcp or rtu")

    # ── TCP settings (mode=tcp) ──────────────────────────────────

    MODBUS_HOST: str = Field("localhost", description="Modbus/TCP server hostname or IP")
    MODBUS_PORT: int = Field(502, ge=1, le=65535, description="Modbus/TCP port (default 502)")

    # ── RTU settings (mode=rtu) ──────────────────────────────────

    MODBUS_SERIAL_PORT: str = Field("", description="Serial port (e.g. COM3, /dev/ttyS0)")
    MODBUS_BAUDRATE: int = Field(9600, description="Serial baud rate")
    MODBUS_BYTESIZE: int = Field(8, ge=5, le=8, description="Serial data bits (5-8)")
    MODBUS_PARITY: str = Field("N", description="Serial parity: N, E, O")
    MODBUS_STOPBITS: int = Field(1, description="Serial stop bits: 1, 2")

    # ── Common settings ──────────────────────────────────────────

    MODBUS_UNIT_ID: int = Field(1, ge=1, le=247, description="Modbus slave/unit ID")
    MODBUS_TIMEOUT: float = Field(3.0, gt=0, description="Request timeout in seconds")
    MODBUS_RETRIES: int = Field(3, ge=0, description="Number of retry attempts")
    MODBUS_POLL_INTERVAL_SEC: float = Field(1.0, gt=0, description="Tag subscription poll interval (seconds)")

    # ── Tag map ──────────────────────────────────────────────────

    MODBUS_TAG_MAP: str = Field(
        "{}",
        description="JSON mapping of logical tag name → register descriptor",
    )

    # ── State tracking ───────────────────────────────────────────

    MODBUS_STATE_TAG: str = Field("", description="Tag name whose value represents equipment state")
    MODBUS_STATE_VALUE_MAP: str = Field(
        "{}",
        description="JSON mapping raw register value (string) → state name string",
    )
    MODBUS_STATE_MODEL_ID: str = Field(
        "",
        description="State model ID to use for transitions (e.g. 'packml', 'semi_e10')",
    )
    MODBUS_EQUIPMENT_ID: str = Field("", description="MES equipment UUID for state tracking")

    model_config = {"env_prefix": "MES_", "extra": "ignore"}

    # ── Parsed helpers ───────────────────────────────────────────

    @field_validator("MODBUS_TAG_MAP", mode="before")
    @classmethod
    def _validate_tag_map(cls, v: str) -> str:
        if v:
            json.loads(v)  # fail fast on invalid JSON
        return v

    @field_validator("MODBUS_STATE_VALUE_MAP", mode="before")
    @classmethod
    def _validate_state_map(cls, v: str) -> str:
        if v:
            json.loads(v)
        return v

    def get_tag_map(self) -> dict[str, dict]:
        """Return the parsed tag map."""
        return json.loads(self.MODBUS_TAG_MAP) if self.MODBUS_TAG_MAP else {}

    def get_state_value_map(self) -> dict[str, str]:
        """Return the parsed state-value map (raw value str → state name)."""
        return json.loads(self.MODBUS_STATE_VALUE_MAP) if self.MODBUS_STATE_VALUE_MAP else {}
