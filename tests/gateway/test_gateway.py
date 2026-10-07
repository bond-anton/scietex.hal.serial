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
except ModuleNotFoundError:
    from scietex.hal.serial.config import ModbusSerialConnectionConfig
    from scietex.hal.serial.gateway.config import (
        GatewayConfig,
        GatewayDeviceConfig,
    )
    from scietex.hal.serial.gateway.gateway import ModbusGateway


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
async def test_start_warns_when_bus_cannot_open(logger_fixture, caplog):
    """A missing serial port logs a warning instead of a healthy start."""
    serial = ModbusSerialConnectionConfig("/dev/does-not-exist-xyz", timeout=0.2)
    config = GatewayConfig(
        serial=serial,
        devices={1: GatewayDeviceConfig(device_id=1, framer="RTU")},
    )
    gw = ModbusGateway(config, logger=logger_fixture)
    with caplog.at_level("WARNING"):
        await gw.start()
    try:
        # Startup still succeeds: the client reconnects on the next request.
        assert gw._bus is not None
        warnings = [
            record
            for record in caplog.records
            if record.levelname == "WARNING" and "could not be opened" in record.getMessage()
        ]
        assert warnings
        assert not any("Gateway bus opened" in record.getMessage() for record in caplog.records)
    finally:
        await gw.stop()


@pytest.mark.asyncio
async def test_start_logs_opened_when_bus_connects(gateway, bus_server, caplog):
    """A reachable serial port logs the healthy-start message, not a warning."""
    await bus_server.start()
    with caplog.at_level("INFO"):
        await gateway.start()
    try:
        assert any(
            record.levelname == "INFO" and "Gateway bus opened" in record.getMessage()
            for record in caplog.records
        )
        assert not any("could not be opened" in record.getMessage() for record in caplog.records)
    finally:
        await gateway.stop()
        await bus_server.stop()


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
