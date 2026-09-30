"""
Utility helpers for serial communication.

This package re-exports the stable public helpers from the ``checksum``,
``numeric``, ``modbus``, and ``serial_port_finder`` submodules so they can be
imported directly from :mod:`scietex.hal.serial.utilities`.
"""

from .checksum import check_sum, lrc, check_lrc
from .numeric import (
    ByteOrder,
    to_signed16,
    from_signed16,
    to_signed32,
    from_signed32,
    combine_32bit,
    split_32bit,
    float_from_int,
    float_to_unsigned16,
    float_from_unsigned16,
    float_from_unsigned32,
)
from .modbus import (
    modbus_connection_config,
    modbus_get_client,
    modbus_execute,
    modbus_read_registers,
    modbus_read_input_registers,
    modbus_read_holding_registers,
    modbus_write_registers,
    modbus_write_register,
)
from .serial_port_finder import find_serial_ports, find_stm32_cdc, find_rs485

__all__ = [
    "check_sum",
    "lrc",
    "check_lrc",
    "ByteOrder",
    "to_signed16",
    "from_signed16",
    "to_signed32",
    "from_signed32",
    "combine_32bit",
    "split_32bit",
    "float_from_int",
    "float_to_unsigned16",
    "float_from_unsigned16",
    "float_from_unsigned32",
    "modbus_connection_config",
    "modbus_get_client",
    "modbus_execute",
    "modbus_read_registers",
    "modbus_read_input_registers",
    "modbus_read_holding_registers",
    "modbus_write_registers",
    "modbus_write_register",
    "find_serial_ports",
    "find_stm32_cdc",
    "find_rs485",
]
