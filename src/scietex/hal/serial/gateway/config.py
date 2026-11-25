"""
Gateway configuration dataclasses.

These dataclasses describe a gateway instance: the serial bus connection, the
TCP listener, and the per-device routing table. They are constructed in code
(by a future service project); this package performs no file I/O, config-dir
resolution, or ENV handling.

Validation runs in ``__post_init__`` and raises `GatewayConfigError`. Plugin
references (framer/decoder/pdu/translator) are validated for resolvability at
construction time, so a bad dotted path fails fast rather than at first request.

Classes:
    - GatewayDeviceConfig: Per-device routing entry.
    - GatewayConfig: Top-level gateway configuration.
"""

import math
from dataclasses import dataclass, field

from ..config import ModbusSerialConnectionConfigModel
from .exceptions import GatewayConfigError
from .plugin_loader import (
    resolve_decoder,
    resolve_framer,
    resolve_pdu,
    resolve_translator,
)

# Modbus device ids are 1..247 (0 is broadcast, 248..255 reserved).
_MIN_DEVICE_ID = 1
_MAX_DEVICE_ID = 247

# Built-in framer shortcuts accepted for the default framer. Uppercase matches
# FramerType member names and ModbusSerialConnectionConfig.framer.
_DEFAULT_FRAMER_CHOICES = ("RTU", "ASCII")

# Substitution for an unset serial timeout. The gateway client already uses the
# same value for the serial transport (``gateway.py``), so the derived budget
# matches the time one bus transaction may actually take.
DEFAULT_SERIAL_TIMEOUT = 3.0

# Fixed settle delay pymodbus adds after a successful connect
# (``AsyncModbusClientMixin.connect``). The hold budget must cover it.
CONNECT_SETTLE_DELAY = 0.1

# Clients the lock-wait budget tolerates queued ahead of the current one. Four
# deferred pollers plus the one on the bus (five concurrent clients) covers the
# ordinary fan-out of an RS485 gateway; anything wider is a load the line
# cannot serve before a client's own timeout fires anyway.
DEFAULT_BUS_QUEUE_DEPTH = 4


def _derived_bus_timeout(serial_timeout: float, bus_retries: int) -> float:
    """Maximum time one bus transaction may hold the lock.

    A transaction first awaits ``_ensure_connected``: the connect attempt is
    bounded by the serial timeout and the client adds a fixed settle sleep.
    Only then does ``execute`` run ``bus_retries + 1`` attempts of one serial
    timeout each.
    """
    return serial_timeout + CONNECT_SETTLE_DELAY + (bus_retries + 1) * serial_timeout


def _resync_overhead(serial_timeout: float) -> float:
    """Bound on the extra lock time one resync may consume.

    A resync closes the transport, reopens it (one serial timeout plus the
    client's fixed settle sleep) and then quarantines the line until the
    abandoned reply window has closed (one serial timeout). The two stages are
    treated as serial rather than overlapping, which over-approximates the
    measured cost: with the quarantine recomputed after the reopen, a slow
    connect eats into the window instead of extending it. The slack is kept
    because the value is also published to clients as part of their timeout.
    """
    return serial_timeout + CONNECT_SETTLE_DELAY + serial_timeout


def _derived_request_timeout(
    bus_timeout: float, serial_timeout: float, bus_queue_depth: int
) -> float:
    """Maximum time a client may wait for the bus lock.

    A client can be queued behind the holder plus ``bus_queue_depth`` waiting
    clients. At most one of the holders ahead of it may have to resync the bus
    after a dirty event, so every holder cycle is budgeted as one hold plus the
    resync bound; one serial timeout of slack follows so the request still gets
    its turn at the head of the queue. Repeated hold expiries can dirty the bus
    again and legitimately exhaust this budget: that is real congestion, not a
    derivation error.
    """
    cycle = bus_timeout + _resync_overhead(serial_timeout)
    return cycle * (bus_queue_depth + 1) + serial_timeout


@dataclass(slots=True)
class GatewayDeviceConfig:
    """
    Per-device routing entry.

    Attributes:
        device_id (int): Modbus device id (1..247).
        framer (str): Framer shortcut ("RTU"/"ASCII") or dotted path.
        decoder (str | None): Dotted path to a custom decoder, or None.
        pdus (list[str]): Dotted paths to custom PDU classes to register.
        translator (str | None): Dotted path to a `GatewayTranslator`, or None
            for pass-through (the device speaks Modbus).
    """

    device_id: int
    framer: str = "RTU"
    decoder: str | None = None
    pdus: list[str] = field(default_factory=list)
    translator: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.device_id, int) or isinstance(self.device_id, bool):
            raise GatewayConfigError(f"device_id must be an int, got: {type(self.device_id)}")
        if not _MIN_DEVICE_ID <= self.device_id <= _MAX_DEVICE_ID:
            raise GatewayConfigError(
                f"device_id must be in {_MIN_DEVICE_ID}..{_MAX_DEVICE_ID}, got: {self.device_id}"
            )
        # Resolvability checks: fail fast on bad plugin references.
        resolve_framer(self.framer)
        if self.decoder is not None:
            resolve_decoder(self.decoder)
        for pdu in self.pdus:
            resolve_pdu(pdu)
        if self.translator is not None:
            resolve_translator(self.translator)


@dataclass(slots=True)
class GatewayCircuitBreakerConfig:
    """
    Per-device circuit breaker settings.

    A device that fails ``failure_threshold`` requests in a row is skipped for
    ``cooldown`` seconds: requests to it return 0x0B immediately without
    touching the bus, so an absent device no longer blocks the devices that
    share the line. After the cooldown the next request probes the device; a
    success closes the circuit, a failure re-opens it for another cooldown.

    Attributes:
        failure_threshold (int): Consecutive failures that open the circuit.
            ``0`` disables the breaker (every request reaches the bus).
        cooldown (float): Seconds to skip a device after the circuit opens.
    """

    failure_threshold: int = 3
    cooldown: float = 30.0

    def __post_init__(self) -> None:
        if not isinstance(self.failure_threshold, int) or isinstance(self.failure_threshold, bool):
            raise GatewayConfigError(
                f"failure_threshold must be an int, got: {type(self.failure_threshold)}"
            )
        if self.failure_threshold < 0:
            raise GatewayConfigError(
                f"failure_threshold cannot be negative, got: {self.failure_threshold}"
            )
        if not isinstance(self.cooldown, (int, float)) or isinstance(self.cooldown, bool):
            raise GatewayConfigError(f"cooldown must be a number, got: {type(self.cooldown)}")
        if self.cooldown < 0:
            raise GatewayConfigError(f"cooldown cannot be negative, got: {self.cooldown}")


@dataclass(slots=True)
class GatewayConfig:
    """
    Top-level gateway configuration.

    Attributes:
        serial (ModbusSerialConnectionConfigModel): Serial bus connection.
        host (str): TCP bind address.
        port (int): TCP bind port (1..65535).
        default_framer (str): Framer used for devices without an explicit entry
            ("RTU" or "ASCII").
        devices (dict[int, GatewayDeviceConfig]): Per-device routing table.
        allow_unknown_devices (bool): If True, devices not in `devices` are
            routed with the default framer; if False, they are rejected.
        bus_retries (int): Retry count for bus transactions.
        circuit_breaker (GatewayCircuitBreakerConfig): Per-device circuit
            breaker settings.
        bus_queue_depth (int): Clients the lock-wait budget tolerates queued
            ahead of the current request. ``0`` assumes only the client on the
            bus is ahead, i.e. the old single-waiter budget.
        request_timeout (float | None): Maximum seconds a client waits to
            acquire the bus lock. None selects
            ``(bus_timeout + 2 * serial_timeout + 0.1) * (bus_queue_depth + 1)
            + serial_timeout``: one hold per client ahead of it, one resync
            (reconnect plus quarantine) for the single dirty event covered, and
            one serial timeout of slack.
        bus_timeout (float | None): Maximum seconds a single request may hold
            the bus lock, covering the reconnect plus every bus attempt. None
            selects ``serial_timeout + 0.1 + (bus_retries + 1) * serial_timeout``,
            where ``serial_timeout`` is the effective serial timeout (3 s when
            unset). The fixed 0.1 s is pymodbus's post-connect settle sleep.
        resync_window (float): Read-only response window the bus is quarantined
            for after an abandoned transaction. Derived from the effective
            serial timeout at construction.
        client_timeout_floor (float): Read-only lower bound for a client's
            per-request socket timeout:
            ``request_timeout + bus_timeout + 2 * serial_timeout + 0.1``,
            computed once at construction from the concretized budgets. A
            client that times out at or below this value can abandon a request
            the gateway is still able to serve.
    """

    serial: ModbusSerialConnectionConfigModel
    host: str = "0.0.0.0"
    port: int = 502
    default_framer: str = "RTU"
    devices: dict[int, GatewayDeviceConfig] = field(default_factory=dict)
    allow_unknown_devices: bool = False
    bus_retries: int = 0
    circuit_breaker: GatewayCircuitBreakerConfig = field(
        default_factory=GatewayCircuitBreakerConfig
    )
    bus_queue_depth: int = DEFAULT_BUS_QUEUE_DEPTH
    request_timeout: float | None = None
    bus_timeout: float | None = None
    # Frozen at construction: a later mutation of serial.timeout must not change
    # a budget that request_timeout was derived from.
    _resync_window: float = field(init=False, default=0.0, repr=False, compare=False)
    # Also frozen: the floor is the sum of the budgets concretized below. The
    # public fields stay mutable, so re-reading them here could publish a floor
    # that disagrees with the gateway's frozen copy -- or raise on a reset to
    # None -- without the gateway actually waiting any shorter.
    _client_timeout_floor: float = field(init=False, default=0.0, repr=False, compare=False)

    @property
    def resync_window(self) -> float:
        """Seconds the bus is quarantined after an abandoned transaction."""
        return self._resync_window

    @property
    def client_timeout_floor(self) -> float:
        """Lower bound for a client's per-request socket timeout."""
        return self._client_timeout_floor

    def __post_init__(self) -> None:
        if not isinstance(self.serial, ModbusSerialConnectionConfigModel):
            raise GatewayConfigError(
                f"serial must be a ModbusSerialConnectionConfigModel, got: {type(self.serial)}"
            )
        if not isinstance(self.port, int) or isinstance(self.port, bool):
            raise GatewayConfigError(f"port must be an int, got: {type(self.port)}")
        if not 1 <= self.port <= 65535:
            raise GatewayConfigError(f"port must be in 1..65535, got: {self.port}")
        if self.default_framer not in _DEFAULT_FRAMER_CHOICES:
            raise GatewayConfigError(
                f"default_framer must be one of {_DEFAULT_FRAMER_CHOICES}, "
                f"got: {self.default_framer!r}"
            )
        if not isinstance(self.bus_retries, int) or isinstance(self.bus_retries, bool):
            raise GatewayConfigError(f"bus_retries must be an int, got: {type(self.bus_retries)}")
        if self.bus_retries < 0:
            raise GatewayConfigError(f"bus_retries cannot be negative, got: {self.bus_retries}")
        if not isinstance(self.circuit_breaker, GatewayCircuitBreakerConfig):
            raise GatewayConfigError(
                "circuit_breaker must be a GatewayCircuitBreakerConfig, "
                f"got: {type(self.circuit_breaker)}"
            )
        for device_id, device in self.devices.items():
            if device_id != device.device_id:
                raise GatewayConfigError(
                    f"devices key {device_id} does not match device_id {device.device_id}"
                )
        if not isinstance(self.bus_queue_depth, int) or isinstance(self.bus_queue_depth, bool):
            raise GatewayConfigError(
                f"bus_queue_depth must be an int, got: {type(self.bus_queue_depth)}"
            )
        if self.bus_queue_depth < 0:
            raise GatewayConfigError(
                f"bus_queue_depth cannot be negative, got: {self.bus_queue_depth}"
            )

        serial_timeout = (
            self.serial.timeout if self.serial.timeout is not None else DEFAULT_SERIAL_TIMEOUT
        )
        # The resync window sleeps inside the lock, so it has to obey the same
        # rules as the explicit budgets: an infinite or zero window either
        # stalls the bus forever or silently disables the quarantine.
        _validate_budget("resync window", serial_timeout)
        self._resync_window = float(serial_timeout)
        bus_timeout = self.bus_timeout
        if bus_timeout is None:
            bus_timeout = _derived_bus_timeout(serial_timeout, self.bus_retries)
        else:
            _validate_budget("bus_timeout", bus_timeout)
        request_timeout = self.request_timeout
        if request_timeout is None:
            request_timeout = _derived_request_timeout(
                bus_timeout, serial_timeout, self.bus_queue_depth
            )
        else:
            _validate_budget("request_timeout", request_timeout)
        self.bus_timeout = bus_timeout
        self.request_timeout = request_timeout
        # Derived once from the concretized budgets. Validated like the other
        # budgets so a bug in the derivation cannot publish a floor of None,
        # infinity, or zero, which would tell clients any timeout is safe.
        floor = request_timeout + bus_timeout + _resync_overhead(self._resync_window)
        _validate_budget("client_timeout_floor", floor)
        self._client_timeout_floor = float(floor)


def _validate_budget(name: str, value: float) -> None:
    """Reject non-numeric, non-finite, or non-positive request budgets."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise GatewayConfigError(f"{name} must be a number, got: {type(value)}")
    if not math.isfinite(value):
        raise GatewayConfigError(f"{name} must be finite, got: {value}")
    if value <= 0:
        raise GatewayConfigError(f"{name} must be positive, got: {value}")
