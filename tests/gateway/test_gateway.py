"""Test the gateway forwarding core (no TCP)."""

import asyncio

import pytest
from pymodbus.pdu import ExceptionResponse
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersRequest,
    ReadHoldingRegistersResponse,
)

try:
    from src.scietex.hal.serial.config import ModbusSerialConnectionConfig
    from src.scietex.hal.serial.gateway.config import (
        GatewayConfig,
        GatewayDeviceConfig,
    )
    from src.scietex.hal.serial.gateway.gateway import ModbusGateway
    from src.scietex.hal.serial.server.rs485_server import RS485Server
except ModuleNotFoundError:
    from scietex.hal.serial.config import ModbusSerialConnectionConfig
    from scietex.hal.serial.gateway.config import (
        GatewayConfig,
        GatewayDeviceConfig,
    )
    from scietex.hal.serial.gateway.gateway import ModbusGateway
    from scietex.hal.serial.server.rs485_server import RS485Server


@pytest.fixture
def gateway_config(vsp_fixture, single_slave_fixture):
    """Gateway config bound to one end of the virtual pair."""
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[1], timeout=0.5)
    return GatewayConfig(
        serial=serial,
        devices={1: GatewayDeviceConfig(device_id=1, framer="RTU")},
    )


@pytest.fixture
def gateway(gateway_config, logger_fixture):
    """A started gateway."""
    gw = ModbusGateway(gateway_config, logger=logger_fixture)
    return gw


@pytest.fixture
def bus_server(vsp_fixture, single_slave_fixture, logger_fixture):
    """An RS485 server on the other end of the virtual pair."""
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[0], timeout=0.5)
    server = RS485Server(serial, devices=single_slave_fixture, logger=logger_fixture)
    return server


@pytest.mark.asyncio
async def test_forward_read_holding_registers(gateway, bus_server):
    """A standard read request is forwarded and answered."""
    await bus_server.start()
    await gateway.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
        response = await gateway.handle_request(1, request)
        assert isinstance(response, ReadHoldingRegistersResponse)
        assert response.registers == [1, 2]
    finally:
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_unknown_device_rejected(gateway, bus_server):
    """An unknown device id yields exception 0x0B when not allowed."""
    await bus_server.start()
    await gateway.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=99)
        response = await gateway.handle_request(99, request)
        assert isinstance(response, ExceptionResponse)
        assert response.exception_code == 0x0B
    finally:
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_unknown_device_allowed(
    vsp_fixture, single_slave_fixture, logger_fixture, bus_server
):
    """With allow_unknown_devices, an unlisted id uses the default framer."""
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[1], timeout=0.5)
    config = GatewayConfig(serial=serial, allow_unknown_devices=True)
    gw = ModbusGateway(config, logger=logger_fixture)
    await bus_server.start()
    await gw.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        response = await gw.handle_request(1, request)
        assert isinstance(response, ReadHoldingRegistersResponse)
    finally:
        await gw.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_bus_timeout_maps_to_exception(gateway, bus_server):
    """A bus timeout is mapped to exception 0x0B, not raised."""
    # Do not start the server: the bus has nothing to answer.
    await gateway.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        response = await gateway.handle_request(1, request)
        assert isinstance(response, ExceptionResponse)
        assert response.exception_code == 0x0B
    finally:
        await gateway.stop()


@pytest.mark.asyncio
async def test_start_is_idempotent(gateway, bus_server):
    """Calling start twice does not reopen the bus."""
    await bus_server.start()
    await gateway.start()
    bus = gateway._bus
    await gateway.start()
    try:
        assert gateway._bus is bus
    finally:
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_stop_is_idempotent(gateway):
    """Calling stop twice is safe."""
    await gateway.start()
    await gateway.stop()
    await gateway.stop()
    assert gateway._bus is None


@pytest.mark.asyncio
async def test_smart_swap_same_framer_no_swap(gateway, bus_server):
    """Two requests to the same device do not swap the framer twice."""
    await bus_server.start()
    await gateway.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        await gateway.handle_request(1, request)
        framer_after_first = gateway._current_framer
        await gateway.handle_request(1, request)
        assert gateway._current_framer is framer_after_first
    finally:
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_concurrent_requests_serialized(gateway, bus_server):
    """Concurrent requests all complete (lock serializes bus access)."""
    await bus_server.start()
    await gateway.start()
    try:
        requests = [
            gateway.handle_request(1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1))
            for _ in range(5)
        ]
        responses = await asyncio.gather(*requests)
        assert all(isinstance(r, ReadHoldingRegistersResponse) for r in responses)
    finally:
        await gateway.stop()
        await bus_server.stop()
