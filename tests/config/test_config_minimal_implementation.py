"""Test serial config subpackage."""

import pytest

try:
    from src.scietex.hal.serial.config.exceptions import (
        SerialConnectionConfigError,
    )
    from src.scietex.hal.serial.config.serial_connection_implementation import (
        SerialConnectionMinimalConfig as Config,
    )
    from src.scietex.hal.serial.config.defaults import (
        DEFAULT_BAUDRATE_LIST,
        DEFAULT_BAUDRATE,
        DEFAULT_BYTESIZE,
        DEFAULT_BYTESIZE_LIST,
        DEFAULT_PARITY,
        DEFAULT_PARITY_LIST,
        DEFAULT_STOPBITS,
        DEFAULT_STOPBITS_LIST,
    )
except ModuleNotFoundError:
    from scietex.hal.serial.config.exceptions import (
        SerialConnectionConfigError,
    )
    from scietex.hal.serial.config.serial_connection_implementation import (
        SerialConnectionMinimalConfig as Config,
    )
    from scietex.hal.serial.config.defaults import (
        DEFAULT_BAUDRATE_LIST,
        DEFAULT_BAUDRATE,
        DEFAULT_BYTESIZE,
        DEFAULT_BYTESIZE_LIST,
        DEFAULT_PARITY,
        DEFAULT_PARITY_LIST,
        DEFAULT_STOPBITS,
        DEFAULT_STOPBITS_LIST,
    )


def test_constructor_from_dict() -> None:
    """Test config creation from dict"""
    dict_conf_minimal = {"port": "COM1"}
    config = Config(**dict_conf_minimal)
    assert config.port == dict_conf_minimal["port"]
    assert config.baudrate == DEFAULT_BAUDRATE
    assert config.parity == DEFAULT_PARITY
    assert config.bytesize == DEFAULT_BYTESIZE
    assert config.stopbits == DEFAULT_STOPBITS
    dict_conf_full = config.to_dict()
    config = Config(**dict_conf_full)
    assert config.port == dict_conf_full["port"]
    assert config.baudrate == dict_conf_full["baudrate"]
    assert config.parity == dict_conf_full["parity"]
    assert config.bytesize == dict_conf_full["bytesize"]
    assert config.stopbits == dict_conf_full["stopbits"]
    dict_conf_extra = config.to_dict()
    dict_conf_extra.update({"extra key": "some value"})
    config = Config(**dict_conf_extra)
    assert config.port == dict_conf_extra["port"]
    assert config.baudrate == dict_conf_extra["baudrate"]
    assert config.parity == dict_conf_extra["parity"]
    assert config.bytesize == dict_conf_extra["bytesize"]
    assert config.stopbits == dict_conf_extra["stopbits"]


def test_constructor_port() -> None:
    """
    Test constructor and port parameter.
    """
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(None)
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(2)
    with pytest.raises(SerialConnectionConfigError):
        _ = Config("CO")
    for port_name in ("COM1", "/dev/serial0", "/dev/my/path/to/dev"):
        conf = Config(port_name)
        assert conf.port == port_name


def test_constructor_baudrate() -> None:
    """
    Test constructor and baudrate parameter.
    """
    port_name = "COM1"
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, baudrate="9600")
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, baudrate=9601)
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, baudrate=9600.0)
    for baudrate in DEFAULT_BAUDRATE_LIST:
        conf = Config(port_name, baudrate=baudrate)
        assert conf.baudrate == baudrate
    conf = Config(port_name, baudrate=None)
    assert conf.baudrate == DEFAULT_BAUDRATE


def test_constructor_bytesize() -> None:
    """
    Test constructor and bytesize parameter.
    """
    port_name = "COM1"
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, bytesize="8")
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, bytesize=9)
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, bytesize=8.0)
    for bytesize in DEFAULT_BYTESIZE_LIST:
        conf = Config(port_name, bytesize=bytesize)
        assert conf.bytesize == bytesize
    conf = Config(port_name, bytesize=None)
    assert conf.bytesize == DEFAULT_BYTESIZE


def test_constructor_parity() -> None:
    """
    Test constructor and parity parameter.
    """
    port_name = "COM1"
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, parity="n")
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, parity=2)
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, parity=1.0)
    for parity in DEFAULT_PARITY_LIST:
        conf = Config(port_name, parity=parity)
        assert conf.parity == parity
    conf = Config(port_name, parity=None)
    assert conf.parity == DEFAULT_PARITY


def test_constructor_stopbits() -> None:
    """
    Test constructor and stopbits parameter.
    """
    port_name = "COM1"
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, stopbits=3)
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, stopbits=2.0)
    with pytest.raises(SerialConnectionConfigError):
        _ = Config(port_name, stopbits="1")
    for stopbits in DEFAULT_STOPBITS_LIST:
        conf = Config(port_name, stopbits=stopbits)
        assert conf.stopbits == stopbits
    conf = Config(port_name, stopbits=None)
    assert conf.stopbits == DEFAULT_STOPBITS


def test_port_property() -> None:
    """
    Test port property.
    """
    port_name = "COM1"
    conf = Config(port_name)
    with pytest.raises(SerialConnectionConfigError):
        conf.port = None
    with pytest.raises(SerialConnectionConfigError):
        conf.port = 2
    with pytest.raises(SerialConnectionConfigError):
        conf.port = "CO"
    for port in ("COM1", "/dev/serial0", "/dev/my/path/to/dev"):
        conf.port = port
        assert conf.port == port


def test_baudrate() -> None:
    """
    Test port baudrate.
    """
    port_name = "COM1"
    conf = Config(port_name)
    with pytest.raises(SerialConnectionConfigError):
        conf.baudrate = 9600.0
    with pytest.raises(SerialConnectionConfigError):
        conf.baudrate = 2
    with pytest.raises(SerialConnectionConfigError):
        conf.baudrate = "9600"
    for baudrate in DEFAULT_BAUDRATE_LIST:
        conf.baudrate = baudrate
        assert conf.baudrate == baudrate


def test_bytesize() -> None:
    """
    Test port bytesize.
    """
    port_name = "COM1"
    conf = Config(port_name)
    with pytest.raises(SerialConnectionConfigError):
        conf.bytesize = 9
    with pytest.raises(SerialConnectionConfigError):
        conf.bytesize = 8.0
    with pytest.raises(SerialConnectionConfigError):
        conf.bytesize = "8"
    for bytesize in DEFAULT_BYTESIZE_LIST:
        conf.bytesize = bytesize
        assert conf.bytesize == bytesize


def test_parity() -> None:
    """
    Test port parity.
    """
    port_name = "COM1"
    conf = Config(port_name)
    with pytest.raises(SerialConnectionConfigError):
        conf.parity = "o"
    with pytest.raises(SerialConnectionConfigError):
        conf.parity = 1
    with pytest.raises(SerialConnectionConfigError):
        conf.parity = "U"
    for parity in DEFAULT_PARITY_LIST:
        conf.parity = parity
        assert conf.parity == parity


def test_stopbits() -> None:
    """
    Test port stopbits.
    """
    port_name = "COM1"
    conf = Config(port_name)
    with pytest.raises(SerialConnectionConfigError):
        conf.stopbits = 3
    with pytest.raises(SerialConnectionConfigError):
        conf.stopbits = 0
    with pytest.raises(SerialConnectionConfigError):
        conf.stopbits = "1"
    for stopbits in DEFAULT_STOPBITS_LIST:
        conf.stopbits = stopbits
        assert conf.stopbits == stopbits


def test_to_dict() -> None:
    """
    Test to_dict method.
    """
    port_name = "COM2"
    conf_min = Config(port_name)
    expected_dict = {
        "port": conf_min.port,
        "baudrate": conf_min.baudrate,
        "bytesize": conf_min.bytesize,
        "parity": conf_min.parity,
        "stopbits": conf_min.stopbits,
    }
    assert conf_min.to_dict() == expected_dict


if __name__ == "__main__":
    pytest.main()
