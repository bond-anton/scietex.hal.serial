"""End-to-end tests: TCP client -> gateway -> pty -> RS485 server."""

import asyncio
import socket

import pytest
from pymodbus.client import AsyncModbusTcpClient

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


def _free_port() -> int:
    """Pick a free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def bus_server(vsp_fixture, single_slave_fixture, logger_fixture):
    """An RS485 server on one end of the virtual pair."""
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[0], timeout=0.5)
    return RS485Server(serial, devices=single_slave_fixture, logger=logger_fixture)


@pytest.fixture
def gateway_stack(vsp_fixture, single_slave_fixture, logger_fixture):
    """A started gateway + TCP server bound to a free port."""
    port = _free_port()
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[1], timeout=0.5)
    config = GatewayConfig(
        serial=serial,
        host="127.0.0.1",
        port=port,
        devices={1: GatewayDeviceConfig(device_id=1, framer="RTU")},
    )
    gateway = ModbusGateway(config, logger=logger_fixture)
    server = GatewayTcpServer(config, gateway, logger=logger_fixture)
    return gateway, server, port


@pytest.mark.asyncio
async def test_end_to_end_read_holding_registers(bus_server, gateway_stack):
    """A real Modbus/TCP client reads registers through the gateway."""
    gateway, server, port = gateway_stack
    await bus_server.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        response = await client.read_holding_registers(address=0, count=2, device_id=1)
        assert not response.isError()
        assert response.registers == [1, 2]
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_end_to_end_unknown_device(bus_server, gateway_stack):
    """An unknown device id returns a Modbus exception to the TCP client."""
    gateway, server, port = gateway_stack
    await bus_server.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        response = await client.read_holding_registers(address=0, count=1, device_id=99)
        assert response.isError()
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_end_to_end_multiple_requests(bus_server, gateway_stack):
    """Several sequential requests over one TCP connection succeed."""
    gateway, server, port = gateway_stack
    await bus_server.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        for _ in range(3):
            response = await client.read_holding_registers(address=0, count=1, device_id=1)
            assert not response.isError()
            assert response.registers == [1]
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_end_to_end_concurrent_clients(bus_server, gateway_stack):
    """Two TCP clients can use the gateway concurrently."""
    gateway, server, port = gateway_stack
    await bus_server.start()
    await gateway.start()
    await server.start()
    client_a = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    client_b = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client_a.connect()
        await client_b.connect()
        results = await asyncio.gather(
            client_a.read_holding_registers(address=0, count=1, device_id=1),
            client_b.read_holding_registers(address=0, count=1, device_id=1),
        )
        assert all(not r.isError() for r in results)
    finally:
        client_a.close()
        client_b.close()
        await server.stop()
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_server_start_stop_idempotent(gateway_stack):
    """start/stop are idempotent."""
    gateway, server, _ = gateway_stack
    await gateway.start()
    await server.start()
    await server.start()
    await server.stop()
    await server.stop()
    await gateway.stop()
