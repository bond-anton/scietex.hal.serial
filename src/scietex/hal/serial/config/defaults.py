"""
Serial connection config defaults.

This module defines constants for default values used for various serial connection configurations.
These constants represent commonly accepted defaults for serial communication parameters
and serve as a reference point for implementing new configurations.

Constants:
    DEFAULT_BAUDRATE (int): Default baud rate for serial communication (in bps). Typically set to
        9600.
    DEFAULT_BAUDRATE_LIST (tuple[int, ...]): List of supported baud rates for serial communication.
    DEFAULT_BYTESIZE (int): Default byte size (number of data bits) for serial communication.
        Commonly set to 8.
    DEFAULT_BYTESIZE_LIST (tuple[int, int, int, int]): List of supported byte sizes for serial
        communication.
    DEFAULT_PARITY (str): Default parity setting for serial communication. Typically set to "N"
        (no parity).
    DEFAULT_PARITY_LIST (tuple[str, str, str]): List of supported parity settings for serial
        communication.
    DEFAULT_STOPBITS (int): Default number of stop bits for serial communication.
        Typically set to 1.
    DEFAULT_STOPBITS_LIST (tuple[int, int]): List of supported stop bit counts for serial
        communication.
    DEFAULT_TIMEOUT (Union[float, None]): Default timeout value for serial communication. Set to
        None by default, meaning no timeout.
    DEFAULT_FRAMER (str): Default Modbus framer type. Typically set to "RTU" (Remote Terminal Unit).
    DEFAULT_FRAMER_LIST (tuple[str, str]): List of supported Modbus framer types.

These constants aim to simplify the process of configuring serial connections by providing sensible
defaults based on industry standards.
"""

from typing import Union

# Baud Rate Defaults
DEFAULT_BAUDRATE: int = 9600
DEFAULT_BAUDRATE_LIST: tuple[int, ...] = (
    300,
    600,
    1200,
    2400,
    4800,
    9600,
    14400,
    19200,
    38400,
    57600,
    115200,
)

# Byte Size Defaults
DEFAULT_BYTESIZE: int = 8
DEFAULT_BYTESIZE_LIST: tuple[int, int, int, int] = (5, 6, 7, 8)

# Parity Defaults
DEFAULT_PARITY: str = "N"
DEFAULT_PARITY_LIST: tuple[str, str, str] = ("N", "E", "O")

# Stop Bits Defaults
DEFAULT_STOPBITS: int = 1
DEFAULT_STOPBITS_LIST: tuple[int, int] = (1, 2)

# Timeout Defaults
DEFAULT_TIMEOUT: Union[float, None] = None

# Framer Defaults
DEFAULT_FRAMER: str = "RTU"
DEFAULT_FRAMER_LIST: tuple[str, str] = ("RTU", "ASCII")
