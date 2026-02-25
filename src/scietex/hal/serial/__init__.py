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
]
