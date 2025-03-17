"""
Module for defining serial communication configuration models.

This module provides abstract base classes and concrete implementations for serial connection
configuration, supporting customization and extensibility through inheritance and dataclass
implementations.

The following abstract base classes define common attributes required for serial communication:

1. **SerialConnectionMinimalConfigModel**: Provides a minimal set of properties needed for basic
   serial communication, such as port, baud rate, byte size, parity, and stop bits.

2. **SerialConnectionConfigModel**: Extends `SerialConnectionMinimalConfigModel` with additional
   timeout settings like read/write timeouts and inter-byte timeouts.

3. **ModbusSerialConnectionConfigModel**: Extends `SerialConnectionMinimalConfigModel` with
   Modbus-specific properties, including a framer for different Modbus framing types ("RTU",
   "ASCII").

Concrete implementations provided in this module allow for easy creation of serial connection
configurations tailored to specific use cases.

Raises:
    SerialConnectionConfigError: If invalid or missing configuration parameters are detected during
        initialization.

Classes:
    - SerialConnectionMinimalConfig: Concrete implementation of `SerialConnectionMinimalConfigModel`
      for minimal serial connection configurations.
    - SerialConnectionConfig: Concrete implementation of `SerialConnectionConfigModel` that includes
      timeout settings.
    - ModbusSerialConnectionConfig: Concrete implementation of `ModbusSerialConnectionConfigModel`
      with Modbus-specific configuration options.

Attributes:
    - port (str): The serial port identifier (e.g., "COM1" on Windows, "/dev/ttyUSB0" on Linux).
    - baudrate (int): Baud rate for serial communication (default is 9600).
    - bytesize (int): Number of data bits per character (default is 8).
    - parity (str): Parity checking mode ('N', 'E', 'O', 'M', 'S'; default is 'N' for no parity).
    - stopbits (float): Number of stop bits (1, 1.5, or 2; default is 1).
    - timeout (float): Read timeout in seconds (optional).
    - write_timeout (float): Write timeout in seconds (optional).
    - inter_byte_timeout (float): Inter-byte timeout in seconds (optional).
    - framer (str): Modbus framer type ('RTU', 'ASCII') if applicable.

Notes:
    - This module relies on the `dataclasses` library for efficient attribute management.
    - All configuration models can be easily extended via subclassing to support app-specific needs.

"""

# Exceptions
from .exceptions import SerialConnectionConfigError

# Abstract base classes
from .serial_connection_interface import (
    SerialConnectionMinimalConfigModel,
    SerialConnectionConfigModel,
    ModbusSerialConnectionConfigModel,
)

# Concrete implementations
from .serial_connection_implementation import (
    SerialConnectionMinimalConfig,
    SerialConnectionConfig,
    ModbusSerialConnectionConfig,
)
