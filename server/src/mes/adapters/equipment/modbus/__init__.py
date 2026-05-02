"""
Modbus TCP/RTU Equipment Adapter package.

Provides ModbusEquipmentAdapter — a concrete EquipmentAdapter implementation
that reads/writes Modbus coils, discrete inputs, holding registers, and input
registers over TCP (Modbus/TCP) or serial (Modbus RTU).

Install pymodbus: pip install mes-ai[modbus]
"""

from .adapter import ModbusEquipmentAdapter
from .config import ModbusEquipmentSettings, ModbusMode

__all__ = ["ModbusEquipmentAdapter", "ModbusEquipmentSettings", "ModbusMode"]
