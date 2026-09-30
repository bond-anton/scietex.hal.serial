"""Serial communication module"""

from .version import __version__
from .config import (
    SerialConnectionMinimalConfig,
    SerialConnectionConfig,
    ModbusSerialConnectionConfig,
)
from .virtual import VirtualSerialNetwork, VirtualSerialPair
from .client import RS485Client
from .server import RS485Server, ReactiveSequentialDataBlock
from .utilities import check_sum, lrc, check_lrc, ByteOrder, combine_32bit, split_32bit
from .utilities import modbus_get_client, find_serial_ports

__all__ = [
    "__version__",
    "SerialConnectionMinimalConfig",
    "SerialConnectionConfig",
    "ModbusSerialConnectionConfig",
    "VirtualSerialNetwork",
    "VirtualSerialPair",
    "RS485Client",
    "RS485Server",
    "ReactiveSequentialDataBlock",
    "check_sum",
    "lrc",
    "check_lrc",
    "ByteOrder",
    "combine_32bit",
    "split_32bit",
    "modbus_get_client",
    "find_serial_ports",
]
