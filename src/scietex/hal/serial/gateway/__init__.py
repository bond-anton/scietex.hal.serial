"""
Modbus gateway package.

A serial<->TCP Modbus gateway that owns one physical serial port and routes
Modbus requests between TCP/IP clients and the devices on that bus, by device
id. Supports both Modbus devices (RTU/ASCII framing) and non-Modbus vendor
protocols via the `GatewayTranslator` plugin contract.

See ``docs/design/modbus-gateway.md`` and
``docs/design/modbus-gateway-nonstandard.md``.
"""

from .config import GatewayConfig, GatewayDeviceConfig
from .exceptions import GatewayConfigError, GatewayError
from .gateway import ModbusGateway
from .metrics import DeviceCounters, GatewayMetrics
from .plugin_loader import (
    build_framer,
    load_class,
    resolve_decoder,
    resolve_framer,
    resolve_pdu,
    resolve_translator,
)
from .tcp_server import GatewayTcpServer
from .translator import GatewayTranslator

__all__ = [
    "GatewayConfig",
    "GatewayConfigError",
    "GatewayDeviceConfig",
    "GatewayError",
    "GatewayMetrics",
    "GatewayTcpServer",
    "GatewayTranslator",
    "DeviceCounters",
    "ModbusGateway",
    "build_framer",
    "load_class",
    "resolve_decoder",
    "resolve_framer",
    "resolve_pdu",
    "resolve_translator",
]
