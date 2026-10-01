"""Shared fixtures for gateway tests."""

import socket

import pytest

try:
    from src.scietex.hal.serial.config import ModbusSerialConnectionConfig
    from src.scietex.hal.serial.gateway.config import (
        GatewayConfig,
        GatewayDeviceConfig,
    )
    from src.scietex.hal.serial.gateway.gateway import ModbusGateway
    from src.scietex.hal.serial.gateway.tcp_server import GatewayTcpServer
    from src.scietex.hal.serial.server.rs485_server import RS485Server
except ModuleNotFoundError:
    from scietex.hal.serial.config import ModbusSerialConnectionConfig
    from scietex.hal.serial.gateway.config import (
        GatewayConfig,
        GatewayDeviceConfig,
    )
    from scietex.hal.serial.gateway.gateway import ModbusGateway
    from scietex.hal.serial.gateway.tcp_server import GatewayTcpServer
    from scietex.hal.serial.server.rs485_server import RS485Server


@pytest.fixture
def free_port() -> int:
    """Pick a free TCP port.

    The socket is closed before the port is used, so a concurrent process could
    in principle claim it in between. Tests bind immediately after, and the
    window is small enough that this is not a practical concern.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def bus_server(vsp_fixture, single_slave_fixture, logger_fixture):
    """An RS485 server on one end of the virtual pair."""
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[0], timeout=0.5)
    return RS485Server(serial, devices=single_slave_fixture, logger=logger_fixture)


@pytest.fixture
def gateway_config(vsp_fixture):
    """Gateway config bound to the other end of the virtual pair."""
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[1], timeout=0.5)
    return GatewayConfig(
        serial=serial,
        devices={1: GatewayDeviceConfig(device_id=1, framer="RTU")},
    )


@pytest.fixture
def gateway(gateway_config, logger_fixture):
    """A gateway (not started)."""
    return ModbusGateway(gateway_config, logger=logger_fixture)


@pytest.fixture
def gateway_stack(vsp_fixture, logger_fixture, free_port):
    """A gateway + TCP server bound to a free port, sharing one config."""
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[1], timeout=0.5)
    config = GatewayConfig(
        serial=serial,
        host="127.0.0.1",
        port=free_port,
        devices={1: GatewayDeviceConfig(device_id=1, framer="RTU")},
    )
    gateway = ModbusGateway(config, logger=logger_fixture)
    server = GatewayTcpServer(config, gateway, logger=logger_fixture)
    return gateway, server, free_port
