"""Test serial config implementations."""

import pytest

try:
    from src.scietex.hal.serial.config.exceptions import (
        SerialConnectionConfigError,
    )
    from src.scietex.hal.serial.config.serial_connection_implementation import (
        SerialConnectionConfig as Config,
    )
    from src.scietex.hal.serial.config.defaults import DEFAULT_TIMEOUT
except ModuleNotFoundError:
    from scietex.hal.serial.config.exceptions import (
        SerialConnectionConfigError,
    )
    from scietex.hal.serial.config.serial_connection_implementation import (
        SerialConnectionConfig as Config,
    )
    from scietex.hal.serial.config.defaults import DEFAULT_TIMEOUT


def test_constructor_timeout() -> None:
    """
    Test constructor and timeout parameter.
    """
    port_name = "COM1"
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, timeout="0")
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, timeout=-1)
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, timeout=-1.0)
    for timeout in (0, 0.0, 1.0, 2.314, 3, 100):
        conf = Config(port_name, timeout=timeout)
        assert conf.timeout == timeout
    conf = Config(port_name, timeout=None)
    assert conf.timeout == DEFAULT_TIMEOUT


def test_timeout_property() -> None:
    """
    Test timeout property.
    """
    port_name = "COM1"
    conf = Config(port_name, timeout=None)
    with pytest.raises(SerialConnectionConfigError):
        conf.timeout = "0"
    with pytest.raises(SerialConnectionConfigError):
        conf.timeout = -1
    with pytest.raises(SerialConnectionConfigError):
        conf.timeout = -1.0
    for timeout in (0, 0.0, 1.0, 2.314, 3, 100):
        conf.timeout = timeout
        assert conf.timeout == timeout
    conf.timeout = None
    assert conf.timeout == DEFAULT_TIMEOUT


def test_write_timeout_property() -> None:
    """
    Test write_timeout property.
    """
    port_name = "COM1"
    conf = Config(port_name, timeout=None)
    with pytest.raises(SerialConnectionConfigError):
        conf.write_timeout = "0"
    with pytest.raises(SerialConnectionConfigError):
        conf.write_timeout = -1
    with pytest.raises(SerialConnectionConfigError):
        conf.write_timeout = -1.0
    for write_timeout in (0, 0.0, 1.0, 2.314, 3, 100):
        conf.write_timeout = write_timeout
        assert conf.write_timeout == write_timeout
    conf.write_timeout = None
    assert conf.write_timeout == DEFAULT_TIMEOUT


def test_inter_byte_timeout_property() -> None:
    """
    Test inter_byte_timeout property.
    """
    port_name = "COM1"
    conf = Config(port_name, timeout=None)
    with pytest.raises(SerialConnectionConfigError):
        conf.inter_byte_timeout = "0"
    with pytest.raises(SerialConnectionConfigError):
        conf.inter_byte_timeout = -1
    with pytest.raises(SerialConnectionConfigError):
        conf.inter_byte_timeout = -1.0
    for inter_byte_timeout in (0, 0.0, 1.0, 2.314, 3, 100):
        conf.inter_byte_timeout = inter_byte_timeout
        assert conf.inter_byte_timeout == inter_byte_timeout
    conf.inter_byte_timeout = None
    assert conf.inter_byte_timeout == DEFAULT_TIMEOUT


def test_to_dict() -> None:
    """
    Test to_dict method.
    """
    port_name = "COM1"
    conf = Config(port_name, timeout=None)
    expected_dict = {
        "port": conf.port,
        "baudrate": conf.baudrate,
        "bytesize": conf.bytesize,
        "parity": conf.parity,
        "stopbits": conf.stopbits,
        "timeout": conf.timeout,
        "write_timeout": conf.write_timeout,
        "inter_byte_timeout": conf.inter_byte_timeout,
    }
    assert conf.to_dict() == expected_dict


if __name__ == "__main__":
    pytest.main()
