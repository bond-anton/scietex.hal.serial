"""Test serial config validation functions."""

import pytest

try:
    from src.scietex.hal.serial.config.exceptions import (
        SerialConnectionConfigError,
    )
    from src.scietex.hal.serial.config.validation import (
        validate_port,
        validate_baudrate,
        validate_bytesize,
        validate_parity,
        validate_stopbits,
        validate_timeout,
        validate_framer,
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
        DEFAULT_TIMEOUT,
        DEFAULT_FRAMER,
        DEFAULT_FRAMER_LIST,
    )
except ModuleNotFoundError:
    from scietex.hal.serial.config.exceptions import (
        SerialConnectionConfigError,
    )
    from scietex.hal.serial.config.validation import (
        validate_port,
        validate_baudrate,
        validate_bytesize,
        validate_parity,
        validate_stopbits,
        validate_timeout,
        validate_framer,
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
        DEFAULT_TIMEOUT,
        DEFAULT_FRAMER,
        DEFAULT_FRAMER_LIST,
    )


def test_validate_port() -> None:
    """
    Test port name validation function.
    """
    # Port is None.
    with pytest.raises(SerialConnectionConfigError):
        validate_port(None)  # Port is None.
    with pytest.raises(SerialConnectionConfigError):
        validate_port("")  # Port is Empty string.
    with pytest.raises(SerialConnectionConfigError):
        validate_port("ab")  # Port is shorter than 3 character string.
    with pytest.raises(SerialConnectionConfigError):
        validate_port(2)  # Port is not a string.
    validated = validate_port("COM1")  # Port is a valid string.
    assert validated == "COM1"
    validated = validate_port("/dev/serial0")
    assert validated == "/dev/serial0"


def test_validate_baudrate() -> None:
    """
    Test baudrate validation function.
    """
    with pytest.raises(SerialConnectionConfigError):
        validate_baudrate(9600.0)  # Baudrate is not an integer.
    with pytest.raises(SerialConnectionConfigError):
        validate_baudrate("9600")  # Baudrate is not an integer.
    with pytest.raises(SerialConnectionConfigError):
        validate_baudrate(9700)  # Baudrate is not in DEFAULT_BAUDRATE_LIST.
    validated = validate_baudrate(None)  # Baudrate is None.
    assert validated == DEFAULT_BAUDRATE
    for baudrate in DEFAULT_BAUDRATE_LIST:
        validated = validate_baudrate(baudrate)
        assert validated == baudrate


def test_validate_bytesize() -> None:
    """
    Test bytesize validation function.
    """
    # Bytesize is not an integer.
    with pytest.raises(SerialConnectionConfigError):
        validate_bytesize(8.0)
    with pytest.raises(SerialConnectionConfigError):
        validate_bytesize("7")
    # Bytesize is not in DEFAULT_BYTESIZE_LIST.
    with pytest.raises(SerialConnectionConfigError):
        validate_bytesize(9)
    # Bytesize is None.
    validated = validate_bytesize(None)
    assert validated == DEFAULT_BYTESIZE
    for bytesize in DEFAULT_BYTESIZE_LIST:
        validated = validate_bytesize(bytesize)
        assert validated == bytesize


def test_validate_parity() -> None:
    """
    Test parity validation function.
    """
    # Parity is not a string.
    with pytest.raises(SerialConnectionConfigError):
        validate_parity(0)
    with pytest.raises(SerialConnectionConfigError):
        validate_parity(1.0)
    # Parity is not in DEFAULT_PARITY_LIST.
    with pytest.raises(SerialConnectionConfigError):
        validate_parity("UNDEFINED")
    # Parity is None.
    validated = validate_parity(None)
    assert validated == DEFAULT_PARITY
    for parity in DEFAULT_PARITY_LIST:
        validated = validate_parity(parity)
        assert validated == parity


def test_validate_stopbits() -> None:
    """
    Test stopbits validation function.
    """
    # Stopbits is not an integer.
    with pytest.raises(SerialConnectionConfigError):
        validate_stopbits(1.0)
    with pytest.raises(SerialConnectionConfigError):
        validate_stopbits("2")
    # Stopbits is not in DEFAULT_STOPBITS_LIST.
    with pytest.raises(SerialConnectionConfigError):
        validate_stopbits(4)
    # Stopbits is None.
    validated = validate_stopbits(None)
    assert validated == DEFAULT_STOPBITS
    for stopbits in DEFAULT_STOPBITS_LIST:
        validated = validate_stopbits(stopbits)
        assert validated == stopbits


def test_validate_timeout() -> None:
    """
    Test timeout validation function.
    """
    # Timeout is not an integer or a float.
    with pytest.raises(SerialConnectionConfigError):
        validate_timeout("1.0")
    with pytest.raises(SerialConnectionConfigError):
        validate_timeout("2")
    # Negative values
    with pytest.raises(SerialConnectionConfigError):
        validate_timeout(-2)
    with pytest.raises(SerialConnectionConfigError):
        validate_timeout(-1.5)
    # Timeout is None.
    validated = validate_timeout(None)
    assert validated == DEFAULT_TIMEOUT
    # Timeout int and float
    for timeout in (1, 2.0, 3, 0.05):
        validated = validate_timeout(timeout)
        assert isinstance(validated, float)
        assert validated == float(timeout)


def test_validate_framer() -> None:
    """
    Test framer validation function.
    """
    # Framer is not in DEFAULT_FRAMER_LIST.
    with pytest.raises(SerialConnectionConfigError):
        validate_framer("UNDEFINED")
    # Framer is None.
    validated = validate_framer(None)
    assert validated == DEFAULT_FRAMER
    for framer in DEFAULT_FRAMER_LIST:
        validated = validate_framer(framer)
        assert validated == framer


if __name__ == "__main__":
    pytest.main()
