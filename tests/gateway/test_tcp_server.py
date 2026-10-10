"""End-to-end tests: TCP client -> gateway -> pty -> RS485 server."""

import asyncio

import pytest
from pymodbus.client import AsyncModbusTcpClient


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


@pytest.mark.asyncio
async def test_server_telemetry_accessors(gateway_stack):
    """tcp_listening/host/port reflect the listener state and config."""
    gateway, server, port = gateway_stack
    assert server.tcp_listening is False
    assert server.tcp_host == "127.0.0.1"
    assert server.tcp_port == port
    await gateway.start()
    await server.start()
    try:
        assert server.tcp_listening is True
    finally:
        await server.stop()
        await gateway.stop()
    assert server.tcp_listening is False


@pytest.mark.asyncio
async def test_server_client_count_tracks_connections(bus_server, gateway_stack):
    """client_count rises while a client is connected and drops on close."""
    gateway, server, port = gateway_stack
    await bus_server.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        assert server.client_count == 0
        await client.connect()
        response = await client.read_holding_registers(address=0, count=1, device_id=1)
        assert not response.isError()
        assert server.client_count == 1
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await bus_server.stop()
