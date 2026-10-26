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
