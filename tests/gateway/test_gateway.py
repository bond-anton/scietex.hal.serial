"""Test the gateway forwarding core (no TCP)."""

import asyncio
import logging
import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ExceptionResponse
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersRequest,
    ReadHoldingRegistersResponse,
)

try:
    from src.scietex.hal.serial.config import ModbusSerialConnectionConfig
    from src.scietex.hal.serial.gateway.config import (
        GatewayCircuitBreakerConfig,
        GatewayConfig,
        GatewayDeviceConfig,
    )
    from src.scietex.hal.serial.gateway.exceptions import GatewayConfigError
    from src.scietex.hal.serial.gateway.gateway import ModbusGateway
    from src.scietex.hal.serial.server.rs485_server import RS485Server
except ModuleNotFoundError:
    from scietex.hal.serial.config import ModbusSerialConnectionConfig
    from scietex.hal.serial.gateway.config import (
        GatewayCircuitBreakerConfig,
        GatewayConfig,
        GatewayDeviceConfig,
    )
    from scietex.hal.serial.gateway.exceptions import GatewayConfigError
    from scietex.hal.serial.gateway.gateway import ModbusGateway
    from scietex.hal.serial.server.rs485_server import RS485Server


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
async def test_recovers_when_port_appears_after_start(
    vsp_fixture, single_slave_fixture, logger_fixture, tmp_path
):
    """A gateway that failed its initial connect recovers once the port appears.

    The gateway is pointed at a symlink that does not exist yet, so startup
    logs the warning and leaves the transport down. Creating the symlink to a
    live bus port must let the next request reconnect and succeed.
    """
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[0], timeout=0.5)
    bus_server = RS485Server(serial, devices=single_slave_fixture, logger=logger_fixture)
    await bus_server.start()

    late_port = Path(tmp_path) / "late-port"
    gateway_config = GatewayConfig(
        serial=ModbusSerialConnectionConfig(str(late_port), timeout=0.5),
        devices={1: GatewayDeviceConfig(device_id=1, framer="RTU")},
    )
    gw = ModbusGateway(gateway_config, logger=logger_fixture)
    await gw.start()
    try:
        # The port does not exist yet: the request fails with 0x0B.
        request = ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
        before = await gw.handle_request(1, request)
        assert isinstance(before, ExceptionResponse)
        assert before.exception_code == 0x0B

        # The port appears: the next request reconnects and succeeds.
        os.symlink(vsp_fixture.serial_ports[1], late_port)
        after = await gw.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
        )
        assert isinstance(after, ReadHoldingRegistersResponse)
        assert after.registers == [1, 2]
    finally:
        await gw.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_port_gone_after_start_maps_to_exception(gateway, bus_server):
    """A bus that disappears after a healthy start yields 0x0B, not a crash."""
    await bus_server.start()
    await gateway.start()
    try:
        # A healthy request first, so the transport is up.
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        healthy = await gateway.handle_request(1, request)
        assert isinstance(healthy, ReadHoldingRegistersResponse)

        # The bus disappears: the next request fails with 0x0B and the gateway
        # stays up (the transport is dropped, not the gateway).
        await bus_server.stop()
        gone = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        assert isinstance(gone, ExceptionResponse)
        assert gone.exception_code == 0x0B
        assert gateway._bus is not None
    finally:
        await gateway.stop()


@pytest.mark.asyncio
async def test_port_gone_then_returns_recovers(
    vsp_fixture, single_slave_fixture, logger_fixture, caplog
):
    """A port lost after a healthy start recovers once it returns.

    The bus failure is logged, and the next request after the port is back
    reconnects and succeeds.
    """
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[0], timeout=0.5)
    bus_server = RS485Server(serial, devices=single_slave_fixture, logger=logger_fixture)
    await bus_server.start()

    gateway_config = GatewayConfig(
        serial=ModbusSerialConnectionConfig(vsp_fixture.serial_ports[1], timeout=0.5),
        devices={1: GatewayDeviceConfig(device_id=1, framer="RTU")},
    )
    gw = ModbusGateway(gateway_config, logger=logger_fixture)
    await gw.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
        healthy = await gw.handle_request(1, request)
        assert isinstance(healthy, ReadHoldingRegistersResponse)

        # The bus disappears: the request fails and the failure is logged.
        await bus_server.stop()
        with caplog.at_level("ERROR"):
            gone = await gw.handle_request(
                1, ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
            )
        assert isinstance(gone, ExceptionResponse)
        assert gone.exception_code == 0x0B
        assert any("Bus failure for device 1" in record.getMessage() for record in caplog.records)

        # The bus returns: the next request reconnects and succeeds.
        bus_server = RS485Server(serial, devices=single_slave_fixture, logger=logger_fixture)
        await bus_server.start()
        back = await gw.handle_request(1, ReadHoldingRegistersRequest(address=0, count=2, dev_id=1))
        assert isinstance(back, ReadHoldingRegistersResponse)
        assert back.registers == [1, 2]
    finally:
        await gw.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_permission_denied_at_start_recovers_when_restored(
    vsp_fixture, single_slave_fixture, logger_fixture, caplog
):
    """A port that cannot be opened for lack of permission recovers once fixed.

    The initial connect fails with EACCES, startup logs the warning, and the
    next request after the permissions are restored reconnects and succeeds.
    """
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[0], timeout=0.5)
    bus_server = RS485Server(serial, devices=single_slave_fixture, logger=logger_fixture)
    await bus_server.start()

    gateway_port = vsp_fixture.serial_ports[1]
    os.chmod(gateway_port, 0o000)
    gateway_config = GatewayConfig(
        serial=ModbusSerialConnectionConfig(gateway_port, timeout=0.5),
        devices={1: GatewayDeviceConfig(device_id=1, framer="RTU")},
    )
    gw = ModbusGateway(gateway_config, logger=logger_fixture)
    try:
        with caplog.at_level("WARNING"):
            await gw.start()
        assert any(
            record.levelname == "WARNING" and "could not be opened" in record.getMessage()
            for record in caplog.records
        )

        denied = await gw.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
        )
        assert isinstance(denied, ExceptionResponse)
        assert denied.exception_code == 0x0B

        os.chmod(gateway_port, 0o600)
        restored = await gw.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
        )
        assert isinstance(restored, ReadHoldingRegistersResponse)
        assert restored.registers == [1, 2]
    finally:
        os.chmod(gateway_port, 0o600)
        await gw.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_permission_lost_after_connect_recovers_when_restored(
    vsp_fixture, single_slave_fixture, logger_fixture, caplog
):
    """Permissions lost after a healthy connect recover once restored.

    The transport drops (the bus disappears) while the port is unreadable, so
    the reconnect fails with EACCES and the request yields 0x0B. Restoring the
    permissions and the bus lets the next request reconnect and succeed.
    """
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[0], timeout=0.5)
    bus_server = RS485Server(serial, devices=single_slave_fixture, logger=logger_fixture)
    await bus_server.start()

    gateway_port = vsp_fixture.serial_ports[1]
    gateway_config = GatewayConfig(
        serial=ModbusSerialConnectionConfig(gateway_port, timeout=0.5),
        devices={1: GatewayDeviceConfig(device_id=1, framer="RTU")},
    )
    gw = ModbusGateway(gateway_config, logger=logger_fixture)
    await gw.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
        healthy = await gw.handle_request(1, request)
        assert isinstance(healthy, ReadHoldingRegistersResponse)

        # The bus drops and the port becomes unreadable: the reconnect fails.
        await bus_server.stop()
        os.chmod(gateway_port, 0o000)
        with caplog.at_level("ERROR"):
            denied = await gw.handle_request(
                1, ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
            )
        assert isinstance(denied, ExceptionResponse)
        assert denied.exception_code == 0x0B
        assert any("Bus failure for device 1" in record.getMessage() for record in caplog.records)

        # Permissions and the bus return: the next request reconnects.
        os.chmod(gateway_port, 0o600)
        bus_server = RS485Server(serial, devices=single_slave_fixture, logger=logger_fixture)
        await bus_server.start()
        restored = await gw.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
        )
        assert isinstance(restored, ReadHoldingRegistersResponse)
        assert restored.registers == [1, 2]
    finally:
        os.chmod(gateway_port, 0o600)
        await gw.stop()
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


@pytest.mark.asyncio
async def test_reconnect_closes_stale_transport_first(gateway, bus_server):
    """Reconnecting closes the stale transport before opening a new one.

    pyserial opens the port with ``exclusive=True``, so a transport that is
    still open keeps the lock and the reconnect fails with EBUSY -- the gateway
    then answers 0x0B forever. The virtual serial pair used here does not
    enforce that lock, so this asserts the ordering the fix guarantees rather
    than the EBUSY failure itself.
    """
    await bus_server.start()
    await gateway.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        await gateway.handle_request(1, request)

        stale = gateway._bus.ctx.transport
        assert stale is not None
        calls = []
        original_close = gateway._bus.close
        original_connect = gateway._bus.connect

        def tracking_close():
            calls.append("close")
            return original_close()

        async def tracking_connect():
            calls.append("connect")
            return await original_connect()

        gateway._bus.close = tracking_close
        gateway._bus.connect = tracking_connect
        gateway._bus.ctx.connection_lost(None)
        assert gateway._bus.ctx.transport is None

        response = await gateway.handle_request(1, request)
        assert isinstance(response, ReadHoldingRegistersResponse)
        assert response.registers == [1]
        assert calls == ["close", "connect"]
    finally:
        await gateway.stop()
        await bus_server.stop()


def _breaker_gateway(vsp_fixture, logger_fixture, *, threshold=3, cooldown=30.0):
    """A gateway with a circuit breaker and two devices (1 live, 2 absent)."""
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[1], timeout=0.2)
    config = GatewayConfig(
        serial=serial,
        devices={
            1: GatewayDeviceConfig(device_id=1, framer="RTU"),
            2: GatewayDeviceConfig(device_id=2, framer="RTU"),
        },
        circuit_breaker=GatewayCircuitBreakerConfig(failure_threshold=threshold, cooldown=cooldown),
    )
    return ModbusGateway(config, logger=logger_fixture)


@pytest.mark.asyncio
async def test_circuit_opens_after_threshold(vsp_fixture, logger_fixture):
    """A device that fails ``threshold`` times is skipped without touching the bus."""
    # No bus server: every request to device 2 times out.
    gateway = _breaker_gateway(vsp_fixture, logger_fixture, threshold=3)
    await gateway.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=2)
        for _ in range(3):
            response = await gateway.handle_request(2, request)
            assert isinstance(response, ExceptionResponse)
            assert response.exception_code == 0x0B

        runtime = gateway._devices[2]
        assert runtime.open_until is not None

        calls = []
        original_execute = gateway._bus.execute

        async def tracking_execute(*args, **kwargs):
            calls.append(args)
            return await original_execute(*args, **kwargs)

        gateway._bus.execute = tracking_execute
        response = await gateway.handle_request(2, request)
        assert isinstance(response, ExceptionResponse)
        assert response.exception_code == 0x0B
        assert calls == []
    finally:
        await gateway.stop()


@pytest.mark.asyncio
async def test_circuit_skip_does_not_block_other_devices(vsp_fixture, logger_fixture, bus_server):
    """An open circuit on one device leaves a healthy device unaffected."""
    await bus_server.start()
    gateway = _breaker_gateway(vsp_fixture, logger_fixture, threshold=1)
    await gateway.start()
    try:
        gateway._devices[2].open_until = time.monotonic() + 30.0

        live = ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
        response = await gateway.handle_request(1, live)
        assert isinstance(response, ReadHoldingRegistersResponse)
        assert response.registers == [1, 2]
    finally:
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_circuit_half_open_probe_closes_on_success(vsp_fixture, logger_fixture, bus_server):
    """After the cooldown a successful probe closes the circuit."""
    await bus_server.start()
    gateway = _breaker_gateway(vsp_fixture, logger_fixture, threshold=1, cooldown=0.0)
    await gateway.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=2, dev_id=1)
        await gateway.handle_request(1, request)
        runtime = gateway._devices[1]
        runtime.consecutive_failures = 1
        runtime.open_until = time.monotonic() - 1

        response = await gateway.handle_request(1, request)
        assert isinstance(response, ReadHoldingRegistersResponse)
        assert runtime.consecutive_failures == 0
        assert runtime.open_until is None
    finally:
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_circuit_half_open_reopens_on_failure(vsp_fixture, logger_fixture):
    """A failed probe after the cooldown re-opens the circuit."""
    # No bus server: the probe to device 2 times out.
    gateway = _breaker_gateway(vsp_fixture, logger_fixture, threshold=1, cooldown=30.0)
    await gateway.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=2)
        await gateway.handle_request(2, request)
        runtime = gateway._devices[2]
        assert runtime.open_until is not None

        runtime.open_until = time.monotonic() - 1
        response = await gateway.handle_request(2, request)
        assert isinstance(response, ExceptionResponse)
        assert response.exception_code == 0x0B
        assert runtime.open_until is not None
        assert runtime.open_until > time.monotonic()
    finally:
        await gateway.stop()


@pytest.mark.asyncio
async def test_circuit_disabled_when_threshold_zero(vsp_fixture, logger_fixture):
    """``failure_threshold: 0`` disables the breaker: every request reaches the bus."""
    # No bus server: every request to device 2 times out.
    gateway = _breaker_gateway(vsp_fixture, logger_fixture, threshold=0)
    await gateway.start()
    try:
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=2)
        for _ in range(5):
            response = await gateway.handle_request(2, request)
            assert isinstance(response, ExceptionResponse)
        assert gateway._devices[2].open_until is None
    finally:
        await gateway.stop()


def _budget_gateway(vsp_fixture, logger_fixture, *, hold_timeout, request_timeout, threshold=3):
    """A gateway with an explicit bus/request budget and two devices."""
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[1], timeout=0.5)
    config = GatewayConfig(
        serial=serial,
        devices={
            1: GatewayDeviceConfig(device_id=1, framer="RTU"),
            2: GatewayDeviceConfig(device_id=2, framer="RTU"),
        },
        bus_timeout=hold_timeout,
        request_timeout=request_timeout,
        circuit_breaker=GatewayCircuitBreakerConfig(failure_threshold=threshold, cooldown=30.0),
    )
    return ModbusGateway(config, logger=logger_fixture)


class _ScriptedBus:
    """A bus stand-in with scripted connect and execute costs and results.

    The last entry of ``connect_results``/``execute_results`` repeats. An
    exception instance in ``execute_results`` is raised instead of returned.
    """

    def __init__(
        self,
        *,
        connect_delay: float = 0.0,
        hold_delay: float = 0.0,
        connect_results: list[bool] | None = None,
        execute_results: list,
    ) -> None:
        self.connect_delay = connect_delay
        self.hold_delay = hold_delay
        self._connect_results = connect_results or [True]
        self._execute_results = execute_results
        self.ctx = SimpleNamespace(transport=object(), framer=None, recv_buffer=b"")
        self.connects = 0
        self.closes = 0
        self.hold_durations: list[float] = []

    def close(self) -> None:
        self.closes += 1
        self.ctx.transport = None

    async def connect(self) -> bool:
        self.connects += 1
        await asyncio.sleep(self.connect_delay)
        result = self._next(self._connect_results)
        if result:
            self.ctx.transport = object()
        return result

    async def execute(self, no_response_expected, request):
        started = time.monotonic()
        await asyncio.sleep(self.hold_delay)
        self.hold_durations.append(time.monotonic() - started)
        result = self._next(self._execute_results)
        if isinstance(result, BaseException):
            raise result
        return result

    @staticmethod
    def _next(results: list):
        return results.pop(0) if len(results) > 1 else results[0]


def _scripted_gateway(
    vsp_fixture, logger_fixture, bus: _ScriptedBus, *, serial_timeout: float = 0.05, **kwargs
):
    """A gateway wired to a scripted bus, without opening a real transport."""
    config = GatewayConfig(
        serial=ModbusSerialConnectionConfig(vsp_fixture.serial_ports[1], timeout=serial_timeout),
        devices={1: GatewayDeviceConfig(device_id=1, framer="RTU")},
        **kwargs,
    )
    gateway = ModbusGateway(config, logger=logger_fixture)
    gateway._build_runtimes()
    gateway._bus = bus
    return gateway, config


@pytest.mark.asyncio
async def test_dirty_bus_lock_wait_covers_one_resync(vsp_fixture, logger_fixture):
    """A queued waiter survives the single resync a dirty bus may add.

    ``request_timeout`` budgets one resync per holder ahead, so a client queued
    behind a dirty holder is not rejected with 0x06 even though the holder's
    occupancy exceeds ``bus_timeout`` by that resync. Repeated hold expiry can
    dirty the bus again and legitimately produce 0x06: that is real congestion,
    not a derivation error. Only one resync per dirty event is covered here.
    """
    serial_timeout = 0.6
    hold_timeout = 1.5
    response = ReadHoldingRegistersResponse(registers=[7])
    bus = _ScriptedBus(
        connect_delay=2 * serial_timeout,
        hold_delay=0.5,
        execute_results=[response],
    )
    gateway, config = _scripted_gateway(
        vsp_fixture,
        logger_fixture,
        bus,
        serial_timeout=serial_timeout,
        bus_timeout=hold_timeout,
        bus_queue_depth=2,
    )
    assert config.request_timeout == pytest.approx(
        (hold_timeout + 2 * serial_timeout + 0.1) * 3 + serial_timeout
    )
    gateway._mark_bus_dirty()
    responses = await asyncio.gather(
        *(
            gateway.handle_request(1, ReadHoldingRegistersRequest(address=index, count=1, dev_id=1))
            for index in range(3)
        )
    )

    assert all(isinstance(item, ReadHoldingRegistersResponse) for item in responses)
    assert all(not isinstance(item, ExceptionResponse) for item in responses)
    # A hold that expires at the budget would be cancelled before it could
    # record its duration, so the gap between the scripted 0.5 s and the 1.5 s
    # budget is wide enough to survive scheduling jitter under ``-n auto``.
    assert max(bus.hold_durations) < hold_timeout
    # One dirty event, one resync; the successful reopen cleared the flag.
    assert bus.connects == 1
    assert bus.closes == 1
    assert gateway._resync_deadline is None


@pytest.mark.asyncio
async def test_resync_success_is_not_repeated_when_the_next_transaction_fails(
    vsp_fixture, logger_fixture
):
    """A completed resync clears the flag even if the following transaction fails.

    An absent device or a pymodbus timeout is exactly the state that armed the
    resync; treating it as "still dirty" would reconnect before every later
    request and reset pymodbus's disconnect accounting each time.
    """
    bus = _ScriptedBus(
        execute_results=[
            ModbusIOException("device gone"),
            ReadHoldingRegistersResponse(registers=[7]),
        ]
    )
    gateway, _ = _scripted_gateway(vsp_fixture, logger_fixture, bus)
    gateway._mark_bus_dirty()
    try:
        first = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        assert isinstance(first, ExceptionResponse)
        assert first.exception_code == 0x0B
        assert bus.connects == 1
        assert bus.closes == 1
        assert gateway._resync_deadline is None

        second = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        assert isinstance(second, ReadHoldingRegistersResponse)
        assert second.registers == [7]
        assert bus.connects == 1
        assert bus.closes == 1
    finally:
        await gateway.stop()


@pytest.mark.asyncio
async def test_resync_quarantine_is_not_extended_by_the_reopen(vsp_fixture, logger_fixture):
    """The quarantine is measured from the deadline, not from the reopen.

    A connect slower than the response window consumes the window instead of
    having a full window appended after it.
    """
    bus = _ScriptedBus(
        connect_delay=1.0,
        execute_results=[ReadHoldingRegistersResponse(registers=[7])],
    )
    gateway, _ = _scripted_gateway(vsp_fixture, logger_fixture, bus, serial_timeout=1.0)
    gateway._mark_bus_dirty()
    started = time.monotonic()
    await gateway._resync_bus(bus)
    elapsed = time.monotonic() - started

    # The connect alone is 1.0 s and consumes the 1.0 s window, so a correct
    # resync returns at ~1.0 s. Appending the full window after the connect
    # would take ~2.0 s: the threshold sits 0.5 s away from either outcome.
    assert elapsed < 1.5
    assert bus.connects == 1
    assert gateway._resync_deadline is None


@pytest.mark.asyncio
async def test_failed_reopen_keeps_the_resync_armed(vsp_fixture, logger_fixture):
    """A failed reopen leaves the flag armed, so the next request retries it."""
    bus = _ScriptedBus(
        connect_results=[False, True],
        execute_results=[ReadHoldingRegistersResponse(registers=[7])],
    )
    gateway, _ = _scripted_gateway(vsp_fixture, logger_fixture, bus)
    gateway._mark_bus_dirty()
    try:
        first = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        assert isinstance(first, ExceptionResponse)
        assert first.exception_code == 0x0B
        assert bus.connects == 1
        assert gateway._resync_deadline is not None

        second = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        assert isinstance(second, ReadHoldingRegistersResponse)
        assert second.registers == [7]
        assert bus.connects == 2
        assert gateway._resync_deadline is None
    finally:
        await gateway.stop()


@pytest.mark.asyncio
async def test_request_exceeding_bus_budget_returns_exception_and_releases_lock(
    vsp_fixture, logger_fixture, bus_server
):
    """A transaction over the hold budget yields 0x0B and does not leak the lock."""
    await bus_server.start()
    gateway = _budget_gateway(vsp_fixture, logger_fixture, hold_timeout=0.05, request_timeout=2.0)
    await gateway.start()
    original_execute = gateway._bus.execute

    async def wedged_execute(*args, **kwargs):
        await asyncio.sleep(10)

    gateway._bus.execute = wedged_execute
    try:
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        started = time.monotonic()
        response = await gateway.handle_request(1, request)
        elapsed = time.monotonic() - started

        assert isinstance(response, ExceptionResponse)
        assert response.exception_code == 0x0B
        assert elapsed < 1.0
        assert not gateway._lock.locked()

        # The lock is usable again once the wedged transaction is cancelled.
        gateway._bus.execute = original_execute
        healthy = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        assert isinstance(healthy, ReadHoldingRegistersResponse)
    finally:
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_request_exceeding_lock_budget_returns_server_device_busy(
    vsp_fixture, logger_fixture, bus_server
):
    """A client that cannot acquire the lock in time gets 0x06, not a stall.

    0x06 tells the caller the server is busy; 0x0B would claim the target
    device failed, although it was never addressed.
    """
    await bus_server.start()
    gateway = _budget_gateway(vsp_fixture, logger_fixture, hold_timeout=5.0, request_timeout=0.1)
    await gateway.start()
    calls = []
    original_execute = gateway._bus.execute

    async def tracking_execute(*args, **kwargs):
        calls.append(args)
        return await original_execute(*args, **kwargs)

    gateway._bus.execute = tracking_execute
    await gateway._lock.acquire()
    try:
        started = time.monotonic()
        response = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        elapsed = time.monotonic() - started

        assert isinstance(response, ExceptionResponse)
        assert response.exception_code == 0x06
        assert elapsed < 1.0
        assert calls == []
        assert gateway._devices[1].consecutive_failures == 0
        # 0x06 means "never addressed": it is not a gateway-level 0x0B error.
        assert gateway.metrics.errors == 0
        assert gateway.metrics.devices[1].errors == 0
    finally:
        gateway._lock.release()
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_wedged_device_does_not_block_a_concurrent_client(
    vsp_fixture, logger_fixture, bus_server
):
    """A live device answers while another device is wedged holding the bus lock."""
    await bus_server.start()
    gateway = _budget_gateway(vsp_fixture, logger_fixture, hold_timeout=0.2, request_timeout=2.0)
    await gateway.start()
    original_execute = gateway._bus.execute

    async def wedged_execute(no_response_expected, request):
        if request.dev_id == 2:
            await asyncio.sleep(10)
        return await original_execute(no_response_expected, request)

    gateway._bus.execute = wedged_execute
    try:
        wedged = asyncio.create_task(
            gateway.handle_request(2, ReadHoldingRegistersRequest(address=0, count=1, dev_id=2))
        )
        # Let the wedged request take the lock first.
        for _ in range(50):
            if gateway._lock.locked():
                break
            await asyncio.sleep(0.01)

        started = time.monotonic()
        live = await asyncio.wait_for(
            gateway.handle_request(1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)),
            timeout=5.0,
        )
        elapsed = time.monotonic() - started

        assert isinstance(live, ReadHoldingRegistersResponse)
        assert live.registers == [1]
        # The live client waits out the holder's 0.2 s budget and the 0.5 s
        # quarantine, so a correct gateway answers at ~0.7 s. An unbounded hold
        # would still be sleeping after 5 s: the wait_for is the wide detector,
        # and 2.0 s keeps a ~1.3 s margin over the fixed cost.
        assert elapsed < 2.0
        assert isinstance(await wedged, ExceptionResponse)
    finally:
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_hold_expiry_arms_the_resync_and_clears_it_on_success(
    vsp_fixture, logger_fixture, bus_server
):
    """An expired transaction forces a reconnect before the next request transmits."""
    await bus_server.start()
    gateway = _budget_gateway(vsp_fixture, logger_fixture, hold_timeout=0.05, request_timeout=3.0)
    await gateway.start()
    original_execute = gateway._bus.execute
    original_close = gateway._bus.close
    original_connect = gateway._bus.connect
    calls = []

    async def wedged_execute(*args, **kwargs):
        await asyncio.sleep(10)

    async def tracking_connect():
        calls.append("connect")
        return await original_connect()

    def tracking_close(*args, **kwargs):
        calls.append("close")
        return original_close(*args, **kwargs)

    gateway._bus.execute = wedged_execute
    gateway._bus.close = tracking_close
    gateway._bus.connect = tracking_connect
    try:
        response = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        assert isinstance(response, ExceptionResponse)
        assert response.exception_code == 0x0B
        assert gateway._resync_deadline is not None
        assert calls == []

        gateway._bus.execute = original_execute
        healthy = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        assert isinstance(healthy, ReadHoldingRegistersResponse)
        assert calls == ["close", "connect"]
        assert gateway._resync_deadline is None
    finally:
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_hold_expiry_detected_when_pymodbus_converts_the_cancellation(
    vsp_fixture, logger_fixture, bus_server
):
    """A hold expiry is still seen when pymodbus turns the cancel into an I/O error.

    On an established transport pymodbus swallows the cancellation and raises
    ``ModbusIOException("Request cancelled outside library.")`` instead of
    propagating it, so a `TimeoutError` branch never fires. The gateway must
    detect the expiry itself and still arm the resync.
    """
    await bus_server.start()
    gateway = _budget_gateway(vsp_fixture, logger_fixture, hold_timeout=0.05, request_timeout=3.0)
    await gateway.start()
    original_execute = gateway._bus.execute

    async def cancelling_execute(*args, **kwargs):
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError as exc:
            raise ModbusIOException("Request cancelled outside library.") from exc

    gateway._bus.execute = cancelling_execute
    try:
        response = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        assert isinstance(response, ExceptionResponse)
        assert response.exception_code == 0x0B
        assert gateway._resync_deadline is not None

        gateway._bus.execute = original_execute
        healthy = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        assert isinstance(healthy, ReadHoldingRegistersResponse)
        assert healthy.registers == [1]
    finally:
        await gateway.stop()
        await bus_server.stop()


class _SlowUnwindBus:
    """A bus whose cancellation handler re-enters the gateway's cleanup.

    pymodbus can swallow the cancellation of an in-flight transaction and only
    finish unwinding later, which keeps the gateway waiting on it. This bus
    reproduces that window deterministically: its cancellation handler cancels
    the surrounding request again, so the second cancel lands while that request
    is still draining this task.
    """

    def __init__(self) -> None:
        self.ctx = SimpleNamespace(transport=object(), framer=None, recv_buffer=b"")
        self.started = asyncio.Event()
        self.request_task: asyncio.Task | None = None

    def close(self) -> None:
        self.ctx.transport = None

    async def connect(self) -> bool:
        self.ctx.transport = object()
        return True

    async def execute(self, no_response_expected, request):
        self.started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            if self.request_task is not None:
                self.request_task.cancel()
            raise


@pytest.mark.asyncio
async def test_cancelled_drain_still_marks_the_bus_dirty(vsp_fixture, logger_fixture):
    """A cancel that lands while the abandoned transaction drains still arms the resync.

    The write is already on the wire when the drain starts, so the mark must run
    on every path out of the cleanup -- including a second cancellation that
    interrupts the wait for the transaction task to finish.
    """
    bus = _SlowUnwindBus()
    gateway, _ = _scripted_gateway(
        vsp_fixture, logger_fixture, bus, serial_timeout=0.2, bus_timeout=5.0
    )
    try:
        walk = asyncio.create_task(
            gateway.handle_request(1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1))
        )
        bus.request_task = walk
        await asyncio.wait_for(bus.started.wait(), timeout=2.0)

        walk.cancel()
        with pytest.raises(asyncio.CancelledError):
            await walk

        assert gateway._resync_deadline is not None
        assert gateway._resync_deadline > time.monotonic()
    finally:
        await gateway.stop()


@pytest.mark.asyncio
async def test_stop_clears_the_resync_deadline(vsp_fixture, logger_fixture):
    """A restarted gateway does not inherit a quarantine measured before the close."""
    bus = _ScriptedBus(execute_results=[ReadHoldingRegistersResponse(registers=[7])])
    gateway, _ = _scripted_gateway(vsp_fixture, logger_fixture, bus)
    gateway._mark_bus_dirty()
    assert gateway._resync_deadline is not None

    await gateway.stop()
    assert gateway._resync_deadline is None


def test_gateway_rejects_a_budget_reset_to_none(vsp_fixture, logger_fixture):
    """A budget cleared after config construction cannot become an unbounded wait."""
    config = GatewayConfig(
        serial=ModbusSerialConnectionConfig(vsp_fixture.serial_ports[1], timeout=0.5)
    )
    config.bus_timeout = None
    with pytest.raises(GatewayConfigError):
        ModbusGateway(config, logger=logger_fixture)

    config.bus_timeout = 1.0
    config.request_timeout = 0
    with pytest.raises(GatewayConfigError):
        ModbusGateway(config, logger=logger_fixture)

    # The resync window sleeps inside the lock, so a zero window is rejected
    # at the same boundary instead of silently disabling the quarantine.
    config.request_timeout = 2.0
    config._resync_window = 0.0
    with pytest.raises(GatewayConfigError):
        ModbusGateway(config, logger=logger_fixture)


@pytest.mark.asyncio
async def test_exception_response_does_not_open_the_breaker(
    vsp_fixture, logger_fixture, bus_server
):
    """A device answering exception responses is alive, so its breaker stays closed.

    The response also reaches the client unchanged.
    """
    await bus_server.start()
    gateway = _budget_gateway(
        vsp_fixture, logger_fixture, hold_timeout=1.0, request_timeout=3.0, threshold=2
    )
    await gateway.start()
    original_execute = gateway._bus.execute
    executed = []

    async def exception_execute(no_response_expected, request):
        executed.append(request.dev_id)
        if request.dev_id == 2:
            return ExceptionResponse(request.function_code, 0x02)
        return await original_execute(no_response_expected, request)

    gateway._bus.execute = exception_execute
    try:
        request = ReadHoldingRegistersRequest(address=0, count=1, dev_id=2)
        for _ in range(5):
            response = await gateway.handle_request(2, request)
            assert isinstance(response, ExceptionResponse)
            # pymodbus marks an exception PDU with the high bit set.
            assert response.function_code == request.function_code | 0x80
            assert response.exception_code == 0x02

        runtime = gateway._devices[2]
        assert runtime.consecutive_failures == 0
        assert runtime.open_until is None
        # Every request reached the bus: the breaker never skipped the device.
        assert executed == [2] * 5

        live = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        assert isinstance(live, ReadHoldingRegistersResponse)
        assert live.registers == [1]
    finally:
        await gateway.stop()
        await bus_server.stop()


@pytest.mark.asyncio
async def test_circuit_logs_unavailable_and_recovered(
    vsp_fixture, logger_fixture, bus_server, caplog
):
    """Opening the circuit logs a WARNING; recovery logs another."""
    await bus_server.start()
    gateway = _breaker_gateway(vsp_fixture, logger_fixture, threshold=1, cooldown=0.0)
    await gateway.start()
    try:
        runtime = gateway._devices[2]
        with caplog.at_level(logging.WARNING):
            gateway._record_failure(2, runtime)
        assert any("unavailable" in r.message for r in caplog.records)

        caplog.clear()
        with caplog.at_level(logging.WARNING):
            gateway._record_success(2, runtime)
        assert any("available again" in r.message for r in caplog.records)
    finally:
        await gateway.stop()
        await bus_server.stop()
