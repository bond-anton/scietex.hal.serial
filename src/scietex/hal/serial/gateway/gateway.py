"""
Modbus gateway forwarding core.

`ModbusGateway` owns one physical serial port (the RS485 bus) and forwards
Modbus requests to devices on that bus by device id. It selects the framer,
decoder, and (optionally) translator per device from configuration.

This module contains the forwarding core only; the TCP listener lives in
`tcp_server.py`. The core is transport-agnostic: `handle_request` takes a
decoded request PDU and returns a response PDU.

Concurrency: the bus is one physical line, so all bus access is serialized by
a single `asyncio.Lock`. The framer is swapped only when the target device's
framer differs from the currently-installed one (smart swap).

Both the wait for the lock and the time a request may hold it are bounded:
`GatewayConfig.request_timeout` (scaled by `GatewayConfig.bus_queue_depth`) and
`GatewayConfig.bus_timeout`. A wedged device therefore costs at most one hold
budget instead of stalling every client on the port indefinitely. A holder that
has to resynchronize the bus adds one bounded resync on top of its hold.

Client contract: a *successful* request can take up to
``request_timeout + bus_timeout + resync`` wall-clock seconds, where ``resync``
is ``2 * serial_timeout + 0.1`` (reconnect plus quarantine). That sum is
published as ``GatewayConfig.client_timeout_floor``; a client's per-request
socket timeout must **exceed** it. When a client times out first it sees only
its own library's timeout -- no Modbus exception PDU, and no gateway metric,
because the gateway cannot observe the disconnect. The request may still be
executing, so a retry queues behind it.

A hold-budget expiry cancels a transaction that is already on the wire, and
pymodbus performs no flush, drain, or reconnect when that happens. RTU frames
carry no usable transaction id, so the abandoned device's late reply would be
accepted as the answer to the next request for the same device id. Expiry
therefore marks the bus dirty; the next client closes and reopens the
transport and lets the response window expire before it transmits
(`ModbusGateway._resync_bus`).

See ``docs/design/modbus-gateway.md`` and
``docs/design/modbus-gateway-nonstandard.md``.
"""

import asyncio
import math
import time
from logging import Logger, getLogger

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException
from pymodbus.framer import FramerBase
from pymodbus.pdu import DecodePDU, ExceptionResponse, ModbusPDU
from pymodbus.transaction import TransactionManager

from .config import GatewayConfig, GatewayDeviceConfig
from .exceptions import GatewayConfigError, GatewayError
from .metrics import GatewayMetrics
from .plugin_loader import (
    build_framer,
    resolve_decoder,
    resolve_framer,
    resolve_pdu,
    resolve_translator,
)

# Modbus exception code for "gateway target device failed to respond".
_TARGET_FAILED = 0x0B
# Modbus exception code for "server device busy": the request was never put on
# the wire, so the target device must not be reported as failed.
_SERVER_DEVICE_BUSY = 0x06


def _resolved_budget(name: str, value: float | None) -> float:
    """
    Freeze a request budget at gateway construction.

    `GatewayConfig` resolves ``None`` to a derived default, but the config is a
    mutable dataclass: a budget that was reset after construction would reach
    ``asyncio.wait_for(timeout=None)`` and wait forever. Validate instead of
    casting the value, and fail at construction where the mistake is made.

    Raises:
        GatewayConfigError: If the budget is missing, non-numeric, non-finite,
            or not positive.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise GatewayConfigError(f"{name} must be a number, got: {value!r}")
    if not math.isfinite(value):
        raise GatewayConfigError(f"{name} must be finite, got: {value}")
    if value <= 0:
        raise GatewayConfigError(f"{name} must be positive, got: {value}")
    return float(value)


class _DeviceRuntime:
    """
    Per-device runtime state: the framer/decoder pair and optional translator.

    Attributes:
        framer (FramerBase): The framer instance for this device.
        translator (GatewayTranslator | None): Translator, or None for pass-through.
        consecutive_failures (int): Failures since the last success.
        open_until (float | None): Monotonic deadline until which the device is
            skipped, or None when the circuit is closed.
    """

    __slots__ = ("framer", "translator", "consecutive_failures", "open_until")

    def __init__(self, framer: FramerBase, translator) -> None:
        self.framer = framer
        self.translator = translator
        self.consecutive_failures = 0
        self.open_until: float | None = None


class ModbusGateway:
    """
    Serial<->TCP Modbus gateway forwarding core.

    Owns one serial bus and routes requests to devices by id, selecting the
    framer/decoder/translator per device from configuration.

    Args:
        config (GatewayConfig): Gateway configuration.
        logger (Logger | None): Optional logger.

    Attributes:
        config (GatewayConfig): The gateway configuration.
        logger (Logger): The logger instance.
    """

    def __init__(self, config: GatewayConfig, logger: Logger | None = None) -> None:
        self.config = config
        self.logger = logger if logger is not None else getLogger(__name__)
        self._bus: AsyncModbusSerialClient | None = None
        self._lock = asyncio.Lock()
        self._current_framer: FramerBase | None = None
        self._devices: dict[int, _DeviceRuntime] = {}
        self._default_runtime: _DeviceRuntime | None = None
        self._metrics = GatewayMetrics()
        # The budgets are frozen here on purpose. `GatewayConfig` resolves None
        # to derived defaults, but it stays mutable, so re-reading a budget at
        # request time could turn `wait_for(timeout=...)` into an unbounded wait.
        self._request_timeout = _resolved_budget("request_timeout", config.request_timeout)
        self._hold_timeout = _resolved_budget("bus_timeout", config.bus_timeout)
        # The resync window sleeps inside the lock, so it is validated like the
        # other budgets: zero would silently disable the quarantine, and inf
        # would sleep forever while holding the bus.
        self._resync_window = _resolved_budget("resync_window", config.resync_window)
        self._resync_deadline: float | None = None

    # -- telemetry ---------------------------------------------------------

    @property
    def metrics(self) -> GatewayMetrics:
        """The live telemetry counters for this gateway."""
        return self._metrics

    @property
    def serial_connected(self) -> bool:
        """Whether the serial transport is currently open."""
        return self._bus is not None and self._bus.ctx.transport is not None

    @property
    def serial_port(self) -> str:
        """The configured serial device path."""
        return self.config.serial.port

    # -- lifecycle ---------------------------------------------------------

    async def start(self) -> None:
        """
        Open the serial bus and build per-device runtime state.

        Idempotent: a second call while running has no effect.

        A failed initial connect does not abort startup: the gateway reconnects
        on the next request (see `_ensure_connected`), so it stays up and
        recovers once the port is available. The failure is logged as a warning
        so a dead bus is not reported as a healthy start.
        """
        if self._bus is not None:
            return
        self._build_runtimes()
        self._bus = self._create_bus()
        if await self._bus.connect():
            self.logger.info("Gateway bus opened on %s", self.config.serial.port)
        else:
            self.logger.warning(
                "Gateway bus could not be opened on %s; will retry on the next request",
                self.config.serial.port,
            )

    async def stop(self) -> None:
        """Close the serial bus. Idempotent."""
        if self._bus is None:
            return
        self._bus.close()
        self._bus = None
        self._current_framer = None
        self.logger.info("Gateway bus closed")

    # -- construction helpers ---------------------------------------------

    def _create_bus(self) -> AsyncModbusSerialClient:
        """Create the serial client with a placeholder framer (swapped per request)."""
        serial = self.config.serial
        client = AsyncModbusSerialClient(
            port=serial.port,
            baudrate=serial.baudrate,
            bytesize=serial.bytesize,
            parity=serial.parity,
            # pymodbus types stopbits as int; the config model allows 1.5 (float),
            # which pyserial accepts at runtime.
            stopbits=serial.stopbits,  # ty: ignore[invalid-argument-type]
            timeout=serial.timeout if serial.timeout is not None else 3,
            retries=self.config.bus_retries,
            name="gateway",
        )
        # Install a default framer so the client is usable before the first swap.
        default_framer = self._build_framer_for(self.config.default_framer, None, [])
        client.ctx = TransactionManager(
            client.comm_params,
            default_framer,
            retries=self.config.bus_retries,
            is_server=False,
            trace_packet=None,
            trace_pdu=None,
            trace_connect=None,
        )
        self._current_framer = default_framer
        return client

    def _build_framer_for(
        self, framer_ref: str, decoder_ref: str | None, pdus: list[str]
    ) -> FramerBase:
        """Build a framer instance with its decoder and registered PDUs."""
        if decoder_ref is not None:
            decoder = resolve_decoder(decoder_ref)(False)
        else:
            decoder = DecodePDU(False)
        for pdu_ref in pdus:
            decoder.register(resolve_pdu(pdu_ref))
        framer_cls = resolve_framer(framer_ref)
        return build_framer(framer_cls, decoder)

    def _build_runtimes(self) -> None:
        """Build the per-device runtime table and the default runtime."""
        self._devices = {}
        for device_id, device in self.config.devices.items():
            self._devices[device_id] = self._build_device_runtime(device)
        self._default_runtime = _DeviceRuntime(
            framer=self._build_framer_for(self.config.default_framer, None, []),
            translator=None,
        )

    def _build_device_runtime(self, device: GatewayDeviceConfig) -> _DeviceRuntime:
        """Build runtime state for one configured device."""
        framer = self._build_framer_for(device.framer, device.decoder, device.pdus)
        translator = None
        if device.translator is not None:
            translator = resolve_translator(device.translator)()
        return _DeviceRuntime(framer=framer, translator=translator)

    def _runtime_for(self, device_id: int) -> _DeviceRuntime:
        """
        Return the runtime for a device id.

        Raises:
            GatewayError: If the device is unknown and unknown devices are not allowed.
        """
        runtime = self._devices.get(device_id)
        if runtime is not None:
            return runtime
        if self.config.allow_unknown_devices and self._default_runtime is not None:
            return self._default_runtime
        raise GatewayError(f"Unknown device id: {device_id}")

    # -- request handling --------------------------------------------------

    async def handle_request(self, device_id: int, request: ModbusPDU) -> ModbusPDU:
        """
        Forward a decoded request to the bus and return a response PDU.

        This is the transport-agnostic entry point used by the TCP server. It
        never raises for bus/device failures: those are mapped to a Modbus
        exception response (0x0B) so the TCP connection stays open. A request
        that could not even reach the bus before its lock-wait budget expired
        returns 0x06 instead, because the target device never failed.

        Args:
            device_id (int): Target device id.
            request (ModbusPDU): The decoded request PDU.

        Returns:
            ModbusPDU: The response PDU (a normal response or an exception response).
        """
        try:
            runtime = self._runtime_for(device_id)
        except GatewayError as exc:
            self.logger.warning("%s", exc)
            self._metrics.record_request(device_id)
            self._metrics.record_error(device_id)
            return ExceptionResponse(request.function_code, _TARGET_FAILED)

        self._metrics.record_request(device_id)
        self._metrics.touch(device_id)
        if self._circuit_open(device_id, runtime):
            self._metrics.record_error(device_id)
            return ExceptionResponse(request.function_code, _TARGET_FAILED)
        try:
            return await self._forward(device_id, request, runtime)
        except (ModbusException, GatewayError, asyncio.TimeoutError) as exc:
            self.logger.error("Bus failure for device %s: %s", device_id, exc)
            self._metrics.record_error(device_id)
            self._record_failure(device_id, runtime)
            return ExceptionResponse(request.function_code, _TARGET_FAILED)

    def _circuit_open(self, device_id: int, runtime: _DeviceRuntime) -> bool:
        """Whether the device is currently skipped by the circuit breaker."""
        if runtime.open_until is None:
            return False
        if time.monotonic() < runtime.open_until:
            return True
        # Cooldown elapsed: let the next request probe the device (half-open).
        runtime.open_until = None
        return False

    def _record_failure(self, device_id: int, runtime: _DeviceRuntime) -> None:
        """Count a failure and open the circuit once the threshold is reached."""
        threshold = self.config.circuit_breaker.failure_threshold
        if threshold == 0:
            return
        runtime.consecutive_failures += 1
        if runtime.consecutive_failures < threshold:
            return
        runtime.open_until = time.monotonic() + self.config.circuit_breaker.cooldown
        self.logger.warning(
            "Device %s unavailable after %d consecutive failures; skipping it for %.1f s",
            device_id,
            runtime.consecutive_failures,
            self.config.circuit_breaker.cooldown,
        )

    def _record_success(self, device_id: int, runtime: _DeviceRuntime) -> None:
        """Close the circuit and log recovery if the device was being skipped."""
        was_open = runtime.open_until is not None
        runtime.consecutive_failures = 0
        runtime.open_until = None
        if was_open:
            self.logger.warning("Device %s is available again", device_id)

    async def _ensure_connected(self) -> None:
        """
        Reconnect the bus if the transport is down.

        The client's ``execute`` raises ``ConnectionException`` when the
        transport is missing instead of reconnecting, so a gateway whose initial
        connect failed would never recover. Reconnecting here makes the
        documented "retry on the next request" behavior real.

        The transport is closed before reconnecting because pyserial opens the
        port with ``exclusive=True``: a still-open transport keeps the lock, so
        the reconnect fails with ``EBUSY`` and the gateway stays wedged. The
        client's own reconnect task is cancelled for the same reason -- it would
        otherwise race this reconnect for the same exclusive lock.

        Raises:
            GatewayError: If the bus is not started or the reconnect fails.
        """
        if self._bus is None:
            raise GatewayError("Gateway bus is not started")
        if self._bus.ctx.transport is not None:
            return
        self._bus.close()
        if not await self._bus.connect():
            raise GatewayError(f"Gateway bus could not be opened on {self.config.serial.port}")

    async def _forward(
        self, device_id: int, request: ModbusPDU, runtime: _DeviceRuntime
    ) -> ModbusPDU:
        """Translate, swap framer, execute, and translate back.

        A request that cannot acquire the lock within ``request_timeout`` is
        rejected with 0x06 without touching the bus; it does not count against
        the device's breaker because the device was never addressed. It is also
        not booked through `GatewayMetrics.record_error`: that counter is
        documented as gateway-level 0x0B failures, and no device failed here.
        The request is still counted by ``record_request``; there is no separate
        busy counter.

        A request whose transaction outlives ``bus_timeout`` is abandoned, which
        leaves its reply in flight: the bus is marked dirty (see `_resync_bus`)
        and the request raises `GatewayError`, which `handle_request` maps to
        0x0B and charges to the target device's breaker.

        A device that answers with an `ExceptionResponse` is healthy: it
        responded promptly, so the breaker is not charged. Counting device
        exceptions would let any network peer open the breaker of a working
        device for ``cooldown`` seconds, and ``isError()`` also flags vendor
        PDUs whose normal function code happens to exceed 0x80.
        """
        bus = self._bus
        if bus is None:
            raise GatewayError("Gateway bus is not started")

        vendor_request = request
        if runtime.translator is not None:
            vendor_request = runtime.translator.to_vendor(request)
        vendor_request.dev_id = device_id

        try:
            await asyncio.wait_for(self._lock.acquire(), timeout=self._request_timeout)
        except asyncio.TimeoutError:
            self.logger.warning(
                "Device %s waited more than %.2f s for the bus; rejecting the request",
                device_id,
                self._request_timeout,
            )
            return ExceptionResponse(request.function_code, _SERVER_DEVICE_BUSY)

        try:
            await self._resync_bus(bus)
            vendor_response = await self._execute_within_hold(
                bus, runtime, vendor_request, device_id
            )
        finally:
            self._lock.release()

        self._metrics.record_retries(device_id, getattr(vendor_response, "retries", 0))
        self._record_success(device_id, runtime)
        if runtime.translator is not None:
            return runtime.translator.to_standard(vendor_response)
        return vendor_response

    async def _execute_within_hold(
        self,
        bus: AsyncModbusSerialClient,
        runtime: _DeviceRuntime,
        vendor_request: ModbusPDU,
        device_id: int,
    ) -> ModbusPDU:
        """Run the transaction and enforce the hold budget at the gateway layer.

        The budget is enforced with `asyncio.wait` rather than
        `asyncio.wait_for`: pymodbus converts the cancellation that `wait_for`
        injects into a ``ModbusIOException`` ("Request cancelled outside
        library") on an established transport, so catching `TimeoutError` never
        fires. Waiting on the task separately makes expiry observable no matter
        what exception pymodbus raises.

        Raises:
            GatewayError: If the budget expired; the bus is marked dirty first.
        """
        task = asyncio.ensure_future(self._transact(bus, runtime, vendor_request))
        try:
            done, _ = await asyncio.wait({task}, timeout=self._hold_timeout)
        except asyncio.CancelledError:
            # An external cancel (shutdown, caller timeout) also abandons an
            # in-flight write, so the bus is just as dirty as a budget expiry.
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            self._mark_bus_dirty()
            raise
        if done:
            return task.result()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        self._mark_bus_dirty()
        raise GatewayError(
            f"Device {device_id} held the bus longer than {self._hold_timeout:.2f} s"
        )

    def _mark_bus_dirty(self) -> None:
        """Arm the resync state after a transaction was abandoned on the wire.

        The abandoned request may still be answered. RTU has no usable
        transaction id and frames are matched by device id, so that reply would
        be taken as the answer to the next request for the same device. The
        window is one response window measured from now: the last write
        happened no later than this instant, and an attempt's reply cannot
        legitimately arrive more than one serial timeout after its write.
        """
        self._resync_deadline = time.monotonic() + self._resync_window
        self.logger.warning(
            "Bus carries an abandoned transaction; resynchronizing before the next request"
        )

    async def _resync_bus(self, bus: AsyncModbusSerialClient) -> None:
        """Close and reopen the transport, then let the abandoned reply window expire.

        Closing the port discards the OS receive buffer; reopening clears
        pymodbus's ``recv_buffer`` and reinstalls the framer. Anything the
        abandoned device sends during the remaining response window is decoded
        against a response future that is already done, so pymodbus drops it.
        The client then transmits only after that window has closed.

        The quarantine deadline is absolute, so the connect overhead is not
        added to it: the sleep is recomputed after the reopen and is 0 when the
        reopen already consumed the window. A successful resync -- reopen plus
        elapsed window -- clears the dirty flag here, independent of the next
        transaction's outcome. A transaction that then fails for an unrelated
        reason (absent device, pymodbus timeout) does not force another
        reconnect. The flag stays armed only when the reopen itself fails, and
        the next request retries the resync.

        Raises:
            GatewayError: If the transport cannot be reopened; the resync state
                stays armed so the next request tries again.
        """
        deadline = self._resync_deadline
        if deadline is None:
            return
        self.logger.warning(
            "Resynchronizing the bus for up to %.2f s after an abandoned transaction",
            max(0.0, deadline - time.monotonic()),
        )
        bus.close()
        # Force `_transact` to reinstall the device framer on the new transport.
        self._current_framer = None
        if not await bus.connect():
            raise GatewayError(f"Gateway bus could not be reopened on {self.config.serial.port}")
        # Recompute after the reopen: a slow connect must not extend the
        # quarantine past the deadline it was measured from.
        remaining = deadline - time.monotonic()
        if remaining > 0:
            await asyncio.sleep(remaining)
        self._resync_deadline = None
        # Drop a partial frame the framer may have buffered while draining.
        bus.ctx.recv_buffer = b""

    async def _transact(
        self,
        bus: AsyncModbusSerialClient,
        runtime: _DeviceRuntime,
        vendor_request: ModbusPDU,
    ) -> ModbusPDU:
        """Reconnect if needed, install the device framer, and execute."""
        await self._ensure_connected()
        if self._current_framer is not runtime.framer:
            bus.ctx.framer = runtime.framer
            self._current_framer = runtime.framer
        return await bus.execute(False, vendor_request)
