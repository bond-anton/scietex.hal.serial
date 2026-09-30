"""Serial communication module"""

from .client import RS485Client
from .config import (
    ModbusSerialConnectionConfig,
    SerialConnectionConfig,
    SerialConnectionMinimalConfig,
)
from .server import ReactiveSequentialDataBlock, RS485Server
from .utilities import (
    ByteOrder,
    ModbusOperationError,
    check_lrc,
    check_sum,
    combine_32bit,
    find_serial_ports,
    lrc,
    modbus_get_client,
    split_32bit,
)
from .version import __version__
from .virtual import VirtualSerialNetwork, VirtualSerialPair

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
    "ModbusOperationError",
]
