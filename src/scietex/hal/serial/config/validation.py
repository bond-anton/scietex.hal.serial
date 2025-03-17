"""
Serial connection config validation routines.

This module provides utility functions for validating various parameters used in serial connection
configurations. Each function checks whether the given parameter meets certain criteria and raises
an appropriate exception if validation fails. These routines help ensure that only valid values are
used throughout the application.

Functions:
    - validate_port(port): Validates the serial port name.
    - validate_baudrate(baudrate): Validates the baud rate.
    - validate_bytesize(bytesize): Validates the number of data bits.
    - validate_parity(parity): Validates the parity setting.
    - validate_stopbits(stopbits): Validates the number of stop bits.
    - validate_timeout(timeout): Validates the timeout value.
    - validate_framer(framer): Validates the Modbus framer type.

Raises:
    SerialConnectionConfigError: If any of the parameters fail validation.

Validation rules:
    - Port names must be non-empty strings and at least 3 characters long.
    - Baud rates must be integers within a predefined list of supported values.
    - Bytesizes must be integers from a predefined list of supported values.
    - Parities must be one of the predefined parity types ('N', 'E', 'O').
    - Stopbits must be either 1 or 2.
    - Timeouts must be non-negative floats or None.
    - Framers must be one of the predefined framer types ('RTU', 'ASCII').

By centralizing validation logic here, we ensure consistent enforcement of constraints across all
configurations.
"""

from typing import Union

from .exceptions import SerialConnectionConfigError
from .defaults import (
    DEFAULT_BAUDRATE,
    DEFAULT_BAUDRATE_LIST,
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


def validate_port(port: Union[str, None]) -> str:
    """
    Validate the port value.

    Ensures that the port name is a non-empty string and has a minimum length of 3 characters.

    Args:
        port (str): Port name to validate.

    Raises:
        SerialConnectionConfigError: If the port is invalid.

    Returns:
        str: Validated port name.
    """
    if not port:
        raise SerialConnectionConfigError("Port cannot be empty")
    if not isinstance(port, str):
        raise SerialConnectionConfigError(f"Port must be a string, got {type(port)}")
    if len(port) < 3:
        raise SerialConnectionConfigError("Port name is too short")
    return port


def validate_baudrate(baudrate: Union[int, None]) -> int:
    """
    Validate the baudrate value.

    Ensures that the baud rate is an integer and falls within the predefined list
    of supported values.

    Args:
        baudrate (int): Baud rate to validate.

    Returns:
        int: Validated baud rate.
    """
    if baudrate is None:
        return DEFAULT_BAUDRATE
    if not isinstance(baudrate, int):
        raise SerialConnectionConfigError(
            f"Baudrate must be integer number, got {type(baudrate)}"
        )
    if baudrate not in DEFAULT_BAUDRATE_LIST:
        raise SerialConnectionConfigError(f"Invalid baudrate: {baudrate}")
    return baudrate


def validate_bytesize(bytesize: Union[int, None]) -> int:
    """
    Validate the bytesize value.

    Ensures that the number of data bits is an integer and falls within the predefined list of
    supported values.

    Args:
        bytesize (int): Number of data bits to validate.

    Returns:
        int: Validated bytesize.
    """
    if bytesize is None:
        return DEFAULT_BYTESIZE
    if not isinstance(bytesize, int):
        raise SerialConnectionConfigError(
            f"Bytesize must be integer number, got {type(bytesize)}"
        )
    if bytesize not in DEFAULT_BYTESIZE_LIST:
        raise SerialConnectionConfigError(f"Invalid bytesize: {bytesize}")
    return bytesize


def validate_parity(parity: Union[str, None]) -> str:
    """
    Validate the parity value.

    Ensures that the parity setting matches one of the predefined parity types ('N', 'E', 'O').

    Args:
        parity (str): Parity value to validate.

    Returns:
        str: Validated parity.
    """
    if parity is None:
        return DEFAULT_PARITY
    if not isinstance(parity, str):
        raise SerialConnectionConfigError(
            f"Parity must be a string, got {type(parity)}"
        )
    if parity not in DEFAULT_PARITY_LIST:
        raise SerialConnectionConfigError(f"Invalid parity: {parity}")
    return parity


def validate_stopbits(stopbits: Union[int, None]) -> int:
    """
    Validate the stopbits value.

    Ensures that the number of stop bits is either 1 or 2.

    Args:
        stopbits (int): Stop bits to validate.

    Returns:
        int: Validated stopbits.
    """
    if stopbits is None:
        return DEFAULT_STOPBITS
    if not isinstance(stopbits, int):
        raise SerialConnectionConfigError(
            f"Stopbits must be integer number, got {type(stopbits)}"
        )
    if stopbits not in DEFAULT_STOPBITS_LIST:
        raise SerialConnectionConfigError(f"Invalid stopbits: {stopbits}")
    return stopbits


def validate_timeout(timeout: Union[float, None]) -> Union[float, None]:
    """
    Validate the timeout value.

    Ensures that the timeout is a non-negative float or None.

    Args:
        timeout (Union[float, None]): Timeout value to validate.

    Returns:
        Union[float, None]: Validated timeout.
    """
    if timeout is None:
        return DEFAULT_TIMEOUT
    if not isinstance(timeout, (float, int)):
        raise SerialConnectionConfigError(
            f"Timeout must be a float, got: {type(timeout)}"
        )
    if timeout < 0:
        raise SerialConnectionConfigError(f"Timeout cannot be negative: {timeout}")
    return float(timeout)


def validate_framer(framer: Union[str, None]) -> str:
    """
    Validate the framer value.

    Ensures that the Modbus framer type matches one of the predefined framer types ('RTU', 'ASCII').

    Args:
        framer (str): Framer value to validate.

    Returns:
        str: Validated framer.
    """
    if framer is None:
        return DEFAULT_FRAMER
    if framer not in DEFAULT_FRAMER_LIST:
        raise SerialConnectionConfigError(f"Unsupported Framer type: {framer}")
    return framer
