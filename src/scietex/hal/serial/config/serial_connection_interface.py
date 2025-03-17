"""
Abstract base classes for serial communication config:

1. **SerialConnectionMinimalConfigModel**: Defines the minimal config for serial
   communication, including properties such as port, baudrate, bytesize, parity, and stopbits.

2. **SerialConnectionConfigModel**: Extends `SerialConnectionMinimalConfigModel` by adding
   timeout-related settings like `timeout`, `write_timeout`, and `inter_byte_timeout`.

3. **ModbusSerialConnectionConfigModel**: Extends `SerialConnectionMinimalConfigModel` by adding
   Modbus-specific config, including the `framer` property for Modbus framing types
   (e.g., "RTU", "ASCII").

These classes are designed to be extended by concrete implementations, providing flexibility in how
serial communication configurations are structured and used in various applications.

Classes:
    SerialConnectionMinimalConfigModel (ABC): Abstract base class for basic serial communication
        config.
    SerialConnectionConfigModel (SerialConnectionMinimalConfigModel): Extended
        serial communication config with timeout settings.
    ModbusSerialConnectionConfigModel (SerialConnectionMinimalConfigModel): Serial communication
        config for Modbus protocol.

Usage:
    To use these models, subclass them to implement the specific behavior for each setting.
    The abstract methods and properties ensure that essential serial connection configurations
    are provided by the subclasses.
"""

from abc import ABC, abstractmethod
from typing import Union


class SerialConnectionMinimalConfigModel(ABC):
    """
    Abstract base class representing the minimal config required for serial communication.

    This class defines the basic config parameters for serial communication, such as port,
    baudrate, bytesize, parity, and stopbits. It also provides abstract methods to convert the
    config to a dictionary format.

    Properties:
        port (str): The name of the serial port.
        baudrate (int): The baud rate for serial communication.
        bytesize (int): The number of data bits.
        parity (str): The parity setting for the communication.
        stopbits (int): The number of stop bits used in the communication.

    Methods:
        to_dict() -> dict: Converts the serial connection config to a dictionary.
    """

    @property
    @abstractmethod
    def port(self) -> str:
        """
        Gets the serial port.

        Returns:
            str: The name of the serial port.
        """

    @port.setter
    @abstractmethod
    def port(self, value: str) -> None:
        """
        Sets the serial port.

        Args:
            value (str): The name of the serial port.
        """

    @property
    @abstractmethod
    def baudrate(self) -> int:
        """
        Gets the baud rate.

        Returns:
            int: The baud rate for serial communication.
        """

    @baudrate.setter
    @abstractmethod
    def baudrate(self, value: int) -> None:
        """
        Sets the baud rate.

        Args:
            value (int): The baud rate for serial communication.
        """

    @property
    @abstractmethod
    def bytesize(self) -> int:
        """
        Gets the number of data bits (bytesize).

        Returns:
            int: The number of data bits.
        """

    @bytesize.setter
    @abstractmethod
    def bytesize(self, value: int) -> None:
        """
        Sets the number of data bits (bytesize).

        Args:
            value (int): The number of data bits.
        """

    @property
    @abstractmethod
    def parity(self) -> str:
        """
        Gets the parity setting.

        Returns:
            str: The parity setting (e.g., "even", "odd", "none").
        """

    @parity.setter
    @abstractmethod
    def parity(self, value: str) -> None:
        """
        Sets the parity setting.

        Args:
            value (str): The parity setting (e.g., "even", "odd", "none").
        """

    @property
    @abstractmethod
    def stopbits(self) -> int:
        """
        Gets the number of stop bits.

        Returns:
            int: The number of stop bits.
        """

    @stopbits.setter
    @abstractmethod
    def stopbits(self, value: int) -> None:
        """
        Sets the number of stop bits.

        Args:
            value (int): The number of stop bits.
        """

    @abstractmethod
    def to_dict(self) -> dict:
        """
        Converts the serial connection config to a dictionary.

        Returns:
            dict: A dictionary representation of the serial connection config.
        """


class SerialConnectionConfigModel(SerialConnectionMinimalConfigModel):
    """
    Extended config model for serial communication, including timeout settings.

    This class builds upon the basic `SerialConnectionMinimalConfigModel` by adding timeout-related
    settings: timeout, write_timeout, and inter_byte_timeout. These values control how long the
    system will wait for various serial operations to complete.

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

    @property
    @abstractmethod
    def timeout(self) -> Union[float, None]:
        """
        Gets the timeout value for the serial connection.

        Returns:
            Union[float, None]: The timeout value in seconds, or None if no timeout is set.
        """

    @timeout.setter
    @abstractmethod
    def timeout(self, value: Union[float, None]) -> None:
        """
        Sets the timeout value for the serial connection.

        Args:
            value (Union[float, None]): Timeout value in seconds, or None to disable the timeout.
        """

    @property
    @abstractmethod
    def write_timeout(self) -> Union[float, None]:
        """
        Gets the write timeout value for the serial connection.

        Returns:
            Union[float, None]: The write timeout value in seconds, or None if no timeout is set.
        """

    @write_timeout.setter
    @abstractmethod
    def write_timeout(self, value: Union[float, None]) -> None:
        """
        Sets the write timeout value for the serial connection.

        Args:
            value (Union[float, None]): Write timeout value in seconds, or None to disable timeout.
        """

    @property
    @abstractmethod
    def inter_byte_timeout(self) -> Union[float, None]:
        """
        Gets the inter-byte timeout value for the serial connection.

        Returns:
            Union[float, None]: Inter-byte timeout value in seconds, or None if no timeout is set.
        """

    @inter_byte_timeout.setter
    @abstractmethod
    def inter_byte_timeout(self, value: Union[float, None]) -> None:
        """
        Sets the inter-byte timeout value for the serial connection.

        Args:
            value (Union[float, None]): Inter-byte timeout in seconds, None to disable timeout.
        """


class ModbusSerialConnectionConfigModel(SerialConnectionMinimalConfigModel):
    """
    Configuration model for Modbus serial communication.

    This class extends the minimal serial connection config and adds a property for
    specifying the Modbus framer, which defines how the Modbus protocol is framed for communication.

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

    @property
    @abstractmethod
    def timeout(self) -> Union[float, None]:
        """
        Gets the timeout value for the serial connection.

        Returns:
            Union[float, None]: The timeout value in seconds, or None if no timeout is set.
        """

    @timeout.setter
    @abstractmethod
    def timeout(self, value: Union[float, None]) -> None:
        """
        Sets the timeout value for the serial connection.

        Args:
            value (Union[float, None]): Timeout value in seconds, or None to disable the timeout.
        """

    @property
    @abstractmethod
    def framer(self) -> str:
        """
        Gets the Modbus framer type.

        Returns:
            str: The type of Modbus framing used (e.g., "RTU", "ASCII").
        """

    @framer.setter
    @abstractmethod
    def framer(self, value: str) -> None:
        """
        Sets the Modbus framer type.

        Args:
            value (str): The type of Modbus framing used (e.g., "RTU", "ASCII").
        """
