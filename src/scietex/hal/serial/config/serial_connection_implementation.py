"""
Implementation of serial connection config interface.

This module provides concrete implementations of the abstract base classes defined in
`serial_connection_interface.py`. Each class represents a specific configuration for serial
communication, adhering to predefined standards and protocols.

The following classes are implemented:

1. **SerialConnectionMinimalConfig**: Implements the minimal required configuration for serial
   communication, including port, baudrate, bytesize, parity, and stopbits.

2. **SerialConnectionConfig**: Extends `SerialConnectionMinimalConfig` by adding timeout-related
   settings like `timeout`, `write_timeout`, and `inter_byte_timeout`.

3. **ModbusSerialConnectionConfig**: Extends `SerialConnectionMinimalConfig` by adding Modbus-
   specific settings, including the `framer` property for Modbus framing types ("RTU", "ASCII").

Each class performs validation of its respective properties using helper functions from the
`validation.py` module.

Example Usage:
>>> from scietex.hal.serial.config import SerialConnectionConfig
>>> config = SerialConnectionConfig(port="/dev/ttyUSB0", baudrate=9600, timeout=1.0)
>>> config.to_dict()
{
    "port": "/dev/ttyUSB0",
    "baudrate": 9600,
    "bytesize": 8,
    "parity": "N",
    "stopbits": 1,
    "timeout": 1.0,
}

Classes:
    - SerialConnectionMinimalConfig: Minimal configuration for serial communication.
    - SerialConnectionConfig: Extended configuration with timeout settings.
    - ModbusSerialConnectionConfig: Config for Modbus serial communication.

Attributes:
    - port (str): The name of the serial port.
    - baudrate (int): The baud rate for serial communication.
    - bytesize (int): The number of data bits.
    - parity (str): The parity setting for the communication.
    - stopbits (int): The number of stop bits used in the communication.
    - timeout (Union[float, None]): The timeout for the serial connection in seconds.
    - write_timeout (Union[float, None]): The write timeout for the serial connection in seconds.
    - inter_byte_timeout (Union[float, None]): The timeout between bytes during transmission.
    - framer (str): The Modbus framer type (e.g., "RTU", "ASCII").

Methods:
    - to_dict() -> dict: Converts the serial connection config to a dictionary.
"""

from typing import Union

from .serial_connection_interface import (
    SerialConnectionMinimalConfigModel,
    SerialConnectionConfigModel,
    ModbusSerialConnectionConfigModel,
)
from .validation import (
    validate_port,
    validate_baudrate,
    validate_bytesize,
    validate_parity,
    validate_stopbits,
    validate_timeout,
    validate_framer,
)


class SerialConnectionMinimalConfig(SerialConnectionMinimalConfigModel):
    """
    Represents the minimal config for a serial connection.

    This class implements the minimal required configuration for serial communication, including
    properties such as port, baudrate, bytesize, parity, and stopbits. Validation is performed
    using helper functions from the `validation.py` module.

    Example:
    >>> config = SerialConnectionMinimalConfig(port="/dev/ttyUSB0", baudrate=9600)
    >>> config.to_dict()
    {
        "port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
    }

    Properties:
        port (str): The name of the serial port.
        baudrate (int): The baud rate for serial communication.
        bytesize (int): The number of data bits.
        parity (str): The parity setting for the communication.
        stopbits (int): The number of stop bits used in the communication.

    Methods:
        to_dict() -> dict: Converts the serial connection config to a dictionary.
    """

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def __init__(
        self,
        port: Union[str, None] = None,
        baudrate: Union[int, None] = None,
        bytesize: Union[int, None] = None,
        parity: Union[str, None] = None,
        stopbits: Union[int, None] = None,
        **kwargs,
    ) -> None:
        self._port: str = validate_port(port)
        self._baudrate = validate_baudrate(baudrate)
        self._bytesize = validate_bytesize(bytesize)
        self._parity = validate_parity(parity)
        self._stopbits = validate_stopbits(stopbits)
        if kwargs is not None:
            # Placeholder for kwargs processing
            pass

    @property
    def port(self) -> str:
        """
        The serial port name (COM1, /dev/serial0, etc.).

        Returns:
            str: The name of the serial port.
        """
        return self._port

    @port.setter
    def port(self, value: str) -> None:
        self._port = validate_port(value)

    @property
    def baudrate(self) -> int:
        """
        The serial port baudrate.

        Returns:
            int: The baudrate of the serial port.
        """
        return self._baudrate

    @baudrate.setter
    def baudrate(self, value: int) -> None:
        self._baudrate = validate_baudrate(value)

    @property
    def bytesize(self) -> int:
        """
        The serial port bytesize.

        Returns:
            int: The bytesize of the serial port.
        """
        return self._bytesize

    @bytesize.setter
    def bytesize(self, value: int) -> None:
        self._bytesize = validate_bytesize(value)

    @property
    def parity(self) -> str:
        """
        The serial port parity. One of ("N", "O", "E").

        Returns:
            str: The parity of the serial port.
        """
        return self._parity

    @parity.setter
    def parity(self, value: str) -> None:
        self._parity = validate_parity(value)

    @property
    def stopbits(self) -> int:
        """
        The serial port stopbits (1 or 2).

        Returns:
            int: The stopbits of the serial port.
        """
        return self._stopbits

    @stopbits.setter
    def stopbits(self, value: int) -> None:
        self._stopbits = validate_stopbits(value)

    def to_dict(self) -> dict:
        """
        Converts the serial connection config to a dictionary.

        Returns:
            dict: A dictionary representation of the serial connection config.
        """
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "bytesize": self.bytesize,
            "parity": self.parity,
            "stopbits": self.stopbits,
        }

    def __str__(self) -> str:
        """
        Human-readable string representation of the object.

        Returns:
            str: A readable description of the configuration.
        """
        return (
            f"Serial Connection Config:\n"
            f"\tPort: {self.port}\n"
            f"\tBaudrate: {self.baudrate}\n"
            f"\tByte Size: {self.bytesize}\n"
            f"\tParity: {self.parity}\n"
            f"\tStop Bits: {self.stopbits}\n"
        )

    def __repr__(self) -> str:
        """
        Technical string representation useful for debugging.

        Returns:
            str: Detailed information about the configuration object.
        """
        return (
            f"{self.__class__.__name__}(port={self.port}, "
            f"baudrate={self.baudrate}, bytesize={self.bytesize}, "
            f"parity='{self.parity}', stopbits={self.stopbits}, "
        )


class SerialConnectionConfig(
    SerialConnectionMinimalConfig, SerialConnectionConfigModel
):
    """
    Serial connection config.

    This class extends `SerialConnectionMinimalConfig` by adding timeout-related settings like
    `timeout`, `write_timeout`, and `inter_byte_timeout`. These settings determine how long the
    system waits for various serial operations to complete.

    Example:
    >>> config = SerialConnectionConfig(port="/dev/ttyUSB0", baudrate=9600, timeout=1.0)
    >>> config.to_dict()
    {
        "port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "timeout": 1.0,
        "write_timeout": None,
        "inter_byte_timeout": None,
    }

    Properties:
        port (str): The name of the serial port.
        baudrate (int): The baud rate for serial communication.
        bytesize (int): The number of data bits.
        parity (str): The parity setting for the communication.
        stopbits (int): The number of stop bits used in the communication.
        timeout (Union[float, None]): The timeout for the serial connection in seconds.
        write_timeout (Union[float, None]): The write timeout for the serial connection in seconds.
        inter_byte_timeout (Union[float, None]): The timeout between bytes during transmission.

    Methods:
        to_dict() -> dict: Converts the serial connection config to a dictionary.
    """

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def __init__(
        self,
        port: Union[str, None] = None,
        baudrate: Union[int, None] = None,
        bytesize: Union[int, None] = None,
        parity: Union[str, None] = None,
        stopbits: Union[int, None] = None,
        timeout: Union[float, None] = None,
        write_timeout: Union[float, None] = None,
        inter_byte_timeout: Union[float, None] = None,
        **kwargs,
    ) -> None:
        super().__init__(port, baudrate, bytesize, parity, stopbits, **kwargs)
        self._timeout = validate_timeout(timeout)
        self._write_timeout = validate_timeout(write_timeout)
        self._inter_byte_timeout = validate_timeout(inter_byte_timeout)

    @property
    def timeout(self) -> Union[float, None]:
        """
        The timeout value for the serial connection.

        Returns:
            value (Union[float, None]): Timeout value in seconds, or None to disable the timeout.
        """
        return self._timeout

    @timeout.setter
    def timeout(self, value: Union[float, None]) -> None:
        self._timeout = validate_timeout(value)

    @property
    def write_timeout(self) -> Union[float, None]:
        """
        The write timeout value for the serial connection.

        Returns:
            Union[float, None]: The write timeout value in seconds, or None if no timeout is set.
        """
        return self._write_timeout

    @write_timeout.setter
    def write_timeout(self, value: Union[float, None]) -> None:
        self._write_timeout = validate_timeout(value)

    @property
    def inter_byte_timeout(self) -> Union[float, None]:
        """
        The inter-byte timeout value for the serial connection.

        Returns:
            Union[float, None]: Inter-byte timeout value in seconds, or None if no timeout is set.
        """
        return self._inter_byte_timeout

    @inter_byte_timeout.setter
    def inter_byte_timeout(self, value: Union[float, None]) -> None:
        self._inter_byte_timeout = validate_timeout(value)

    def to_dict(self) -> dict:
        return super().to_dict() | {
            "timeout": self.timeout,
            "write_timeout": self.write_timeout,
            "inter_byte_timeout": self.inter_byte_timeout,
        }

    def __str__(self) -> str:
        """
        Human-readable string representation of the object.

        Returns:
            str: A readable description of the configuration.
        """
        return (
            f"Serial Connection Config:\n"
            f"\tPort: {self.port}\n"
            f"\tBaudrate: {self.baudrate}\n"
            f"\tByte Size: {self.bytesize}\n"
            f"\tParity: {self.parity}\n"
            f"\tStop Bits: {self.stopbits}\n"
            f"\tTimeout: {self.timeout}\n"
            f"\tWrite Timeout: {self.write_timeout}\n"
            f"\tInter-Byte Timeout: {self.inter_byte_timeout}"
        )

    def __repr__(self) -> str:
        """
        Technical string representation useful for debugging.

        Returns:
            str: Detailed information about the configuration object.
        """
        return (
            f"{self.__class__.__name__}(port={self.port}, "
            f"baudrate={self.baudrate}, bytesize={self.bytesize}, "
            f"parity='{self.parity}', stopbits={self.stopbits}, "
            f"timeout={self.timeout}, write_timeout={self.write_timeout}, "
            f"inter_byte_timeout={self.inter_byte_timeout})"
        )


class ModbusSerialConnectionConfig(
    SerialConnectionMinimalConfig, ModbusSerialConnectionConfigModel
):
    """
    Modbus serial connection config.

    This class extends `SerialConnectionMinimalConfig` by adding Modbus-specific settings, including
    the `framer` property for Modbus framing types ("RTU", "ASCII"). Additionally, it supports
    timeout settings similar to `SerialConnectionConfig`.

    Example:
    >>> config = ModbusSerialConnectionConfig(port="/dev/ttyUSB0", baudrate=9600, framer="RTU")
    >>> config.to_dict()
    {
        "port": "/dev/ttyUSB0",
        "baudrate": 9600,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "timeout": None,
        "framer": "RTU",
    }

    Properties:
        port (str): The name of the serial port.
        baudrate (int): The baud rate for serial communication.
        bytesize (int): The number of data bits.
        parity (str): The parity setting for the communication.
        stopbits (int): The number of stop bits used in the communication.
        timeout (Union[float, None]): The timeout for the serial connection in seconds.
        framer (str): The Modbus framer type (e.g., "RTU", "ASCII").

    Methods:
        to_dict() -> dict: Converts the serial connection config to a dictionary.
    """

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def __init__(
        self,
        port: Union[str, None] = None,
        baudrate: Union[int, None] = None,
        bytesize: Union[int, None] = None,
        parity: Union[str, None] = None,
        stopbits: Union[int, None] = None,
        timeout: Union[float, None] = None,
        framer: Union[str, None] = None,
        **kwargs,
    ) -> None:
        super().__init__(port, baudrate, bytesize, parity, stopbits, **kwargs)
        self._timeout = validate_timeout(timeout)
        self._framer = validate_framer(framer)

    @property
    def timeout(self) -> Union[float, None]:
        """
        The timeout value for the serial connection.

        Returns:
            value (Union[float, None]): Timeout value in seconds, or None to disable the timeout.
        """
        return self._timeout

    @timeout.setter
    def timeout(self, value: Union[float, None]) -> None:
        self._timeout = validate_timeout(value)

    @property
    def framer(self) -> str:
        """
        The Modbus framer type.

        Returns:
            str: The type of Modbus framing used (e.g., "RTU", "ASCII").
        """
        return self._framer

    @framer.setter
    def framer(self, value: str) -> None:
        self._framer = validate_framer(value)

    def to_dict(self) -> dict:
        return super().to_dict() | {"framer": self.framer, "timeout": self.timeout}

    def __str__(self) -> str:
        """
        Human-readable string representation of the object.

        Returns:
            str: A readable description of the configuration.
        """
        return (
            f"Modbus Connection Config:\n"
            f"\tPort: {self.port}\n"
            f"\tBaudrate: {self.baudrate}\n"
            f"\tByte Size: {self.bytesize}\n"
            f"\tParity: {self.parity}\n"
            f"\tStop Bits: {self.stopbits}\n"
            f"\tTimeout: {self.timeout}\n"
        )

    def __repr__(self) -> str:
        """
        Technical string representation useful for debugging.

        Returns:
            str: Detailed information about the configuration object.
        """
        return (
            f"{self.__class__.__name__}(port={self.port}, "
            f"baudrate={self.baudrate}, bytesize={self.bytesize}, "
            f"parity='{self.parity}', stopbits={self.stopbits}, "
            f"timeout={self.timeout}"
        )
