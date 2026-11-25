"""Test the gateway configuration dataclasses."""

import pytest

try:
    from src.scietex.hal.serial.config import ModbusSerialConnectionConfig
    from src.scietex.hal.serial.gateway.config import (
        GatewayConfig,
        GatewayDeviceConfig,
    )
    from src.scietex.hal.serial.gateway.exceptions import GatewayConfigError
except ModuleNotFoundError:
    from scietex.hal.serial.config import ModbusSerialConnectionConfig
    from scietex.hal.serial.gateway.config import (
        GatewayConfig,
        GatewayDeviceConfig,
    )
    from scietex.hal.serial.gateway.exceptions import GatewayConfigError


@pytest.fixture
def serial_config() -> ModbusSerialConnectionConfig:
    """A minimal valid serial connection config."""
    return ModbusSerialConnectionConfig(port="/dev/ttyUSB0")


def test_device_config_defaults() -> None:
    """Defaults are applied and resolvable."""
    device = GatewayDeviceConfig(device_id=1)
    assert device.framer == "RTU"
    assert device.decoder is None
    assert device.pdus == []
    assert device.translator is None


@pytest.mark.parametrize("device_id", [0, 248, -1, 1000])
def test_device_config_rejects_out_of_range_id(device_id: int) -> None:
    """Device ids outside 1..247 are rejected."""
    with pytest.raises(GatewayConfigError):
        GatewayDeviceConfig(device_id=device_id)


def test_device_config_rejects_non_int_id() -> None:
    """A non-int device id is rejected."""
    with pytest.raises(GatewayConfigError):
        GatewayDeviceConfig(device_id="1")  # type: ignore[arg-type]


def test_device_config_rejects_bad_framer() -> None:
    """An unresolvable framer reference is rejected at construction."""
    with pytest.raises(GatewayConfigError):
        GatewayDeviceConfig(device_id=1, framer="SOCKET")


def test_device_config_rejects_bad_decoder() -> None:
    """An unresolvable decoder reference is rejected at construction."""
    with pytest.raises(GatewayConfigError):
        GatewayDeviceConfig(device_id=1, decoder="no_such_module.Decoder")


def test_device_config_rejects_bad_pdu() -> None:
    """An unresolvable PDU reference is rejected at construction."""
    with pytest.raises(GatewayConfigError):
        GatewayDeviceConfig(device_id=1, pdus=["no_such_module.Pdu"])


def test_device_config_rejects_bad_translator() -> None:
    """An unresolvable translator reference is rejected at construction."""
    with pytest.raises(GatewayConfigError):
        GatewayDeviceConfig(device_id=1, translator="no_such_module.Translator")


def test_device_config_accepts_dotted_framer() -> None:
    """A dotted-path framer resolves."""
    device = GatewayDeviceConfig(device_id=1, framer="pymodbus.framer.FramerRTU")
    assert device.framer == "pymodbus.framer.FramerRTU"


def test_gateway_config_defaults(serial_config: ModbusSerialConnectionConfig) -> None:
    """Top-level defaults are applied."""
    config = GatewayConfig(serial=serial_config)
    assert config.host == "0.0.0.0"
    assert config.port == 502
    assert config.default_framer == "RTU"
    assert config.devices == {}
    assert config.allow_unknown_devices is False
    assert config.bus_retries == 0


def test_gateway_config_rejects_bad_serial() -> None:
    """A non-config serial object is rejected."""
    with pytest.raises(GatewayConfigError):
        GatewayConfig(serial="not-a-config")  # type: ignore[arg-type]


@pytest.mark.parametrize("port", [0, 65536, -1])
def test_gateway_config_rejects_bad_port(
    serial_config: ModbusSerialConnectionConfig, port: int
) -> None:
    """Ports outside 1..65535 are rejected."""
    with pytest.raises(GatewayConfigError):
        GatewayConfig(serial=serial_config, port=port)


def test_gateway_config_rejects_bad_default_framer(
    serial_config: ModbusSerialConnectionConfig,
) -> None:
    """default_framer must be a built-in shortcut."""
    with pytest.raises(GatewayConfigError):
        GatewayConfig(serial=serial_config, default_framer="SOCKET")


def test_gateway_config_rejects_negative_retries(
    serial_config: ModbusSerialConnectionConfig,
) -> None:
    """bus_retries cannot be negative."""
    with pytest.raises(GatewayConfigError):
        GatewayConfig(serial=serial_config, bus_retries=-1)


def test_gateway_config_rejects_mismatched_device_key(
    serial_config: ModbusSerialConnectionConfig,
) -> None:
    """A devices key that disagrees with device_id is rejected."""
    device = GatewayDeviceConfig(device_id=1)
    with pytest.raises(GatewayConfigError):
        GatewayConfig(serial=serial_config, devices={2: device})


def test_gateway_config_accepts_valid_devices(
    serial_config: ModbusSerialConnectionConfig,
) -> None:
    """A consistent devices table is accepted."""
    device = GatewayDeviceConfig(device_id=1)
    config = GatewayConfig(serial=serial_config, devices={1: device})
    assert config.devices[1] is device


def test_gateway_config_derives_request_budgets_from_timeout_and_retries() -> None:
    """Unset budgets follow the serial timeout, retry count, and queue depth."""
    serial = ModbusSerialConnectionConfig("/dev/ttyUSB0", timeout=0.5)
    config = GatewayConfig(serial=serial, bus_retries=2)
    # One connect (0.5 s) + the client's 0.1 s settle sleep + 3 attempts of 0.5 s.
    assert config.bus_timeout == 2.1
    assert config.resync_window == 0.5
    # The holder plus four queued clients, each up to one hold plus one resync
    # (2 * 0.5 s + 0.1 s), plus one serial timeout of slack.
    assert config.request_timeout == (2.1 + 1.1) * 5 + 0.5
    assert config.client_timeout_floor == 16.5 + 2.1 + 1.1


def test_gateway_config_default_budgets_use_three_second_fallback() -> None:
    """An unset serial timeout falls back to 3 s, as the bus client does."""
    config = GatewayConfig(serial=ModbusSerialConnectionConfig("/dev/ttyUSB0"))
    assert config.serial.timeout is None
    # 3 s connect + 0.1 s settle + one 3 s attempt.
    assert config.bus_timeout == 6.1
    assert config.resync_window == 3.0
    assert config.request_timeout == (6.1 + 6.1) * 5 + 3.0
    assert config.client_timeout_floor == 64.0 + 6.1 + 6.1


def test_gateway_config_scales_the_lock_wait_with_queue_depth() -> None:
    """The lock wait covers the holder plus ``bus_queue_depth`` queued clients."""
    serial = ModbusSerialConnectionConfig("/dev/ttyUSB0", timeout=0.5)
    narrow = GatewayConfig(serial=serial, bus_queue_depth=1)
    wide = GatewayConfig(serial=serial, bus_queue_depth=8)
    hold = narrow.bus_timeout
    resync = 2 * 0.5 + 0.1
    assert narrow.request_timeout == (hold + resync) * 2 + 0.5
    assert wide.request_timeout == (hold + resync) * 9 + 0.5


def test_gateway_config_zero_queue_depth_covers_only_the_holder() -> None:
    """``bus_queue_depth=0`` restores the single-holder budget."""
    serial = ModbusSerialConnectionConfig("/dev/ttyUSB0", timeout=0.5)
    config = GatewayConfig(serial=serial, bus_queue_depth=0)
    assert config.request_timeout == (config.bus_timeout + 2 * 0.5 + 0.1) * 1 + 0.5


@pytest.mark.parametrize(
    ("serial_timeout", "queue_depth", "bus_timeout", "lock_wait", "client_floor"),
    [
        # B = t + 0.1 + (r + 1) * t, s = 2t + 0.1.
        (1.0, 2, 2.1, (2.1 + 2.1) * 3 + 1.0, 13.6 + 2.1 + 2.1),
        (1.0, 4, 2.1, (2.1 + 2.1) * 5 + 1.0, 22.0 + 2.1 + 2.1),
        (3.0, 4, 6.1, (6.1 + 6.1) * 5 + 3.0, 64.0 + 6.1 + 6.1),
    ],
)
def test_gateway_config_publishes_the_client_timeout_floor(
    serial_timeout: float,
    queue_depth: int,
    bus_timeout: float,
    lock_wait: float,
    client_floor: float,
) -> None:
    """``client_timeout_floor`` is the lock wait plus one hold and one resync."""
    config = GatewayConfig(
        serial=ModbusSerialConnectionConfig("/dev/ttyUSB0", timeout=serial_timeout),
        bus_queue_depth=queue_depth,
    )
    assert config.bus_timeout == bus_timeout
    assert config.request_timeout == lock_wait
    assert config.client_timeout_floor == client_floor


@pytest.mark.parametrize("timeout", [0.0, float("inf"), float("nan")])
def test_gateway_config_rejects_bad_resync_window(
    serial_config: ModbusSerialConnectionConfig, timeout: float
) -> None:
    """The resync window is validated like the other budgets."""
    serial_config.timeout = timeout
    with pytest.raises(GatewayConfigError):
        GatewayConfig(serial=serial_config, bus_timeout=1.0)


def test_gateway_config_freezes_the_resync_window(
    serial_config: ModbusSerialConnectionConfig,
) -> None:
    """A serial timeout mutation after construction cannot change the window."""
    serial_config.timeout = 0.5
    config = GatewayConfig(serial=serial_config)
    serial_config.timeout = 5.0
    assert config.resync_window == 0.5


@pytest.mark.parametrize("depth", [-1, 1.5, "2"])
def test_gateway_config_rejects_bad_queue_depth(
    serial_config: ModbusSerialConnectionConfig, depth
) -> None:
    """The queue depth must be a non-negative int."""
    with pytest.raises(GatewayConfigError):
        GatewayConfig(serial=serial_config, bus_queue_depth=depth)


def test_gateway_config_preserves_explicit_budgets() -> None:
    """Explicit budgets override the derived values."""
    config = GatewayConfig(
        serial=ModbusSerialConnectionConfig("/dev/ttyUSB0", timeout=0.5),
        bus_timeout=0.25,
        request_timeout=1.25,
    )
    assert config.bus_timeout == 0.25
    assert config.request_timeout == 1.25


@pytest.mark.parametrize("budget", [0, -1, "1.0", float("inf"), float("nan")])
def test_gateway_config_rejects_bad_budgets(
    serial_config: ModbusSerialConnectionConfig, budget
) -> None:
    """Budgets must be positive finite numbers."""
    with pytest.raises(GatewayConfigError):
        GatewayConfig(serial=serial_config, bus_timeout=budget)
    with pytest.raises(GatewayConfigError):
        GatewayConfig(serial=serial_config, request_timeout=budget)
