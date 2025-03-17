"""Test modbus config implementations."""

import pytest

try:
    from src.scietex.hal.serial.config.exceptions import (
        SerialConnectionConfigError,
    )
    from src.scietex.hal.serial.config.serial_connection_implementation import (
        ModbusSerialConnectionConfig as Config,
    )
    from src.scietex.hal.serial.config.defaults import (
        DEFAULT_TIMEOUT,
        DEFAULT_FRAMER,
        DEFAULT_FRAMER_LIST,
    )
except ModuleNotFoundError:
    from scietex.hal.serial.config.exceptions import (
        SerialConnectionConfigError,
    )
    from scietex.hal.serial.config.serial_connection_implementation import (
        ModbusSerialConnectionConfig as Config,
    )
    from scietex.hal.serial.config.defaults import (
        DEFAULT_TIMEOUT,
        DEFAULT_FRAMER,
        DEFAULT_FRAMER_LIST,
    )


def test_constructor_timeout() -> None:
    """
    Test constructor and timeout parameter.
    """
    port_name = "COM1"
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, timeout="1")
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, timeout=-2)
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, timeout=-2.0)
    for timeout in (0, 0.00, 1.1, 2.214, 5, 500):
        conf = Config(port_name, timeout=timeout)
        assert conf.timeout == timeout
    config = Config(port_name, timeout=None)
    assert config.timeout == DEFAULT_TIMEOUT


def test_constructor_framer() -> None:
    """
    Test constructor and framer parameter.
    """
    port_name = "COM1"
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, framer="ascii")
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, framer="TCP")
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, framer=1)
    for framer in DEFAULT_FRAMER_LIST:
        conf = Config(port_name, framer=framer)
        assert conf.framer == framer
    conf = Config(port_name, framer=None)
    assert conf.framer == DEFAULT_FRAMER


def test_timeout_property() -> None:
    """
    Test timeout property.
    """
    port_name = "COM1"
    conf_mb = Config(port_name, timeout=None)
    with pytest.raises(SerialConnectionConfigError):
        conf_mb.timeout = "0"
    with pytest.raises(SerialConnectionConfigError):
        conf_mb.timeout = -1
    with pytest.raises(SerialConnectionConfigError):
        conf_mb.timeout = -1.0
    for timeout in (0, 0.0, 1.0, 2.314, 3, 100):
        conf_mb.timeout = timeout
        assert conf_mb.timeout == timeout
    conf_mb.timeout = None
    assert conf_mb.timeout == DEFAULT_TIMEOUT


def test_framer_property() -> None:
    """
    Test framer property.
    """
    port_name = "COM1"
    conf_mb = Config(port_name, framer=DEFAULT_FRAMER)
    with pytest.raises(SerialConnectionConfigError):
        conf_mb.framer = "ascii"
    with pytest.raises(SerialConnectionConfigError):
        conf_mb.framer = "TCP"
    with pytest.raises(SerialConnectionConfigError):
        conf_mb.framer = 1
    for framer in DEFAULT_FRAMER_LIST:
        conf_mb.framer = framer
        assert conf_mb.framer == framer
    conf_mb.framer = None
    assert conf_mb.framer == DEFAULT_FRAMER


def test_to_dict() -> None:
    """
    Test to_dict method.
    """
    port_name = "COM3"
    conf_modbus = Config(port_name)
    expected_dict = {
        "port": conf_modbus.port,
        "baudrate": conf_modbus.baudrate,
        "bytesize": conf_modbus.bytesize,
        "parity": conf_modbus.parity,
        "stopbits": conf_modbus.stopbits,
        "timeout": conf_modbus.timeout,
        "framer": conf_modbus.framer,
    }
    assert conf_modbus.to_dict() == expected_dict


if __name__ == "__main__":
    pytest.main()
