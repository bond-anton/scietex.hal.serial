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
