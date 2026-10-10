"""Test gateway telemetry counters."""

import pytest
from pymodbus.pdu import ExceptionResponse
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersRequest,
    ReadHoldingRegistersResponse,
)

try:
    from src.scietex.hal.serial.gateway.metrics import GatewayMetrics
except ModuleNotFoundError:
    from scietex.hal.serial.gateway.metrics import GatewayMetrics


def test_metrics_start_zeroed():
    """A fresh metrics object has no counters and no devices."""
    metrics = GatewayMetrics()
    assert metrics.requests == 0
    assert metrics.errors == 0
    assert metrics.retries == 0
    assert metrics.devices == {}


def test_record_request_creates_device_counters():
    """Recording a request bumps the total and the per-device counter."""
    metrics = GatewayMetrics()
    metrics.record_request(1)
    metrics.record_request(1)
    metrics.record_request(2)
    assert metrics.requests == 3
    assert metrics.devices[1].requests == 2
    assert metrics.devices[2].requests == 1


def test_record_error_bumps_total_and_device():
    """Recording an error bumps the total and the per-device error counter."""
    metrics = GatewayMetrics()
    metrics.record_error(1)
    assert metrics.errors == 1
    assert metrics.devices[1].errors == 1


def test_record_retries_ignores_zero():
    """Zero retries do not change the counter."""
    metrics = GatewayMetrics()
    metrics.record_retries(1, 0)
    assert metrics.retries == 0


def test_record_retries_accumulates():
    """Observed retries accumulate across requests."""
    metrics = GatewayMetrics()
    metrics.record_retries(1, 2)
    metrics.record_retries(1, 1)
    assert metrics.retries == 3


def test_touch_sets_last_seen():
    """Touching a device stamps its last-seen time."""
    metrics = GatewayMetrics()
    assert metrics.devices.get(1) is None
    metrics.touch(1)
    assert metrics.devices[1].last_seen is not None


@pytest.mark.asyncio
async def test_gateway_counts_successful_request(gateway, bus_server):
    """A successful request bumps requests and last_seen, not errors."""
    await bus_server.start()
    await gateway.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
        response = await gateway.handle_request(1, request)
        assert isinstance(response, ReadHoldingRegistersResponse)
        assert gateway.metrics.requests == 1
        assert gateway.metrics.errors == 0
        assert gateway.metrics.devices[1].requests == 1
        assert gateway.metrics.devices[1].last_seen is not None
    finally:
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_gateway_counts_unknown_device_error(gateway, bus_server):
    """An unknown device counts as a request and an error."""
    await bus_server.start()
    await gateway.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=99)
        response = await gateway.handle_request(99, request)
        assert isinstance(response, ExceptionResponse)
        assert gateway.metrics.requests == 1
        assert gateway.metrics.errors == 1
        assert gateway.metrics.devices[99].errors == 1
    finally:
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_gateway_counts_bus_failure(gateway):
    """A bus timeout counts as a request and an error."""
    await gateway.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        response = await gateway.handle_request(1, request)
        assert isinstance(response, ExceptionResponse)
        assert gateway.metrics.requests == 1
        assert gateway.metrics.errors == 1
    finally:
        await gateway.stop()


@pytest.mark.asyncio
async def test_gateway_serial_connected_reflects_transport(gateway, bus_server):
    """serial_connected is False before start and True once the bus is open."""
    assert gateway.serial_connected is False
    await bus_server.start()
    await gateway.start()
    try:
        assert gateway.serial_connected is True
    finally:
        await gateway.stop()
        await bus_server.stop()
    assert gateway.serial_connected is False


@pytest.mark.asyncio
async def test_gateway_serial_port_matches_config(gateway, gateway_config):
    """serial_port exposes the configured device path."""
    assert gateway.serial_port == gateway_config.serial.port
