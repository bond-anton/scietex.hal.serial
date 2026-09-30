"""
Utility helpers for serial communication.

This package re-exports the stable public helpers from the ``checksum``,
``numeric``, ``modbus``, and ``serial_port_finder`` submodules so they can be
imported directly from :mod:`scietex.hal.serial.utilities`.
"""

from .checksum import check_lrc, check_sum, lrc
from .exceptions import ModbusOperationError
from .modbus import (
    modbus_connection,
    modbus_connection_config,
    modbus_execute,
    modbus_get_client,
    modbus_read_holding_registers,
    modbus_read_input_registers,
    modbus_read_registers,
    modbus_write_register,
    modbus_write_registers,
)
from .numeric import (
    ByteOrder,
    combine_32bit,
    float_from_int,
    float_from_unsigned16,
    float_from_unsigned32,
    float_to_unsigned16,
    from_signed16,
    from_signed32,
    split_32bit,
    to_signed16,
    to_signed32,
)
from .serial_port_finder import find_rs485, find_serial_ports, find_stm32_cdc

__all__ = [
    "check_sum",
    "lrc",
    "check_lrc",
    "ModbusOperationError",
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
    "modbus_connection",
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
