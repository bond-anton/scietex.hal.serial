"""
RS485 Client Module.

This module provides a client implementation for communicating with Modbus devices over an RS485
serial interface. It leverages the `pymodbus` library to handle Modbus requests and responses,
offering a simple yet powerful way to interact with remote devices.

Key Features:
    - Supports asynchronous operations for efficient communication.
    - Handles common Modbus commands like reading and writing registers.
    - Facilitates logging of client activities for debugging and monitoring.

This module simplifies interaction with Modbus devices over RS485, making it easier to integrate
with industrial automation systems and IoT applications.
"""

from typing import Union, Optional, Any
from logging import Logger, getLogger

from pymodbus.pdu import ModbusPDU, DecodePDU
from pymodbus.framer import FramerBase
from pymodbus.client import AsyncModbusSerialClient

from ..config import (
    SerialConnectionConfigModel,
    ModbusSerialConnectionConfigModel,
)
from ..utilities.modbus import (
    modbus_get_client,
    modbus_execute,
    modbus_read_registers,
    modbus_write_registers,
)

from ..utilities.numeric import (
    ByteOrder,
    to_signed16,
    from_signed16,
    to_signed32,
    from_signed32,
    float_from_int,
    float_to_unsigned16,
    float_from_unsigned16,
    float_from_unsigned32,
    combine_32bit,
    split_32bit,
)


class RS485Client:
    """
    RS485 Client for communicating with Modbus devices over an RS485 serial interface.

    This class provides methods to read and write Modbus registers, handle float and integer
    conversions, and manage communication with the device. It supports both holding and input
    registers, as well as custom framers, decoders, and response handlers.

    Args:
        con_params (Union[SerialConnectionConfigModel, ModbusSerialConnectionConfigModel]):
            Configuration parameters for the serial connection.
        address (int, optional):
            The slave address of the Modbus device. Defaults to 1.
        label (str, optional):
            A label for the client, used for logging and identification. Defaults to "RS485 Device".
        custom_framer (Optional[type[FramerBase]], optional):
            A custom framer class for handling Modbus message framing. Defaults to None.
        custom_decoder (Optional[type[DecodePDU]], optional):
            A custom decoder class for decoding Modbus Protocol Data Units (PDUs). Defaults to None.
        custom_response (Optional[list[type[ModbusPDU]]], optional):
            A list of custom Modbus PDU response types to be registered with the client.
            Defaults to None.
        logger (Optional[Logger], optional):
            A logger instance for logging client activities. If not provided, a default logger
            is used.

    Attributes:
        con_params (Union[SerialConnectionConfigModel, ModbusSerialConnectionConfigModel]):
            Configuration parameters for the serial connection.
        client (AsyncModbusSerialClient):
            The Modbus client instance used for communication.
        address (int):
            The slave address of the Modbus device.
        label (str):
            A label for the client, used for logging and identification.
        logger (Logger):
            The logger instance used for logging client activities.
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        con_params: Union[
            SerialConnectionConfigModel, ModbusSerialConnectionConfigModel
        ],
        address: int = 1,
        label: str = "RS485 Device",
        custom_framer: Optional[type[FramerBase]] = None,
        custom_decoder: Optional[type[DecodePDU]] = None,
        custom_response: Optional[list[type[ModbusPDU]]] = None,
        logger: Optional[Logger] = None,
    ):
        self.con_params: Union[
            SerialConnectionConfigModel, ModbusSerialConnectionConfigModel
        ] = con_params
        self.client: AsyncModbusSerialClient = modbus_get_client(
            con_params, custom_framer, custom_decoder, custom_response, label
        )

        self.address: int = address
        self.label: str = label
        self.logger: Logger
        if logger is None:
            self.logger = getLogger()
        else:
            self.logger = logger

    async def execute(
        self, request: ModbusPDU, no_response_expected: bool = False
    ) -> Optional[ModbusPDU]:
        """
        Execute a Modbus request asynchronously.

        Args:
            request (ModbusPDU):
                The Modbus Protocol Data Unit (PDU) representing the request to be sent.
            no_response_expected (bool, optional):
                If True, indicates that no response is expected from the device. Defaults to False.

        Returns:
            Optional[ModbusPDU]:
                The response from the device as a Modbus PDU. Returns None if an error occurs or
                no response is expected.
        """
        return await modbus_execute(
            self.client, request, no_response_expected, self.logger
        )

    async def read_registers(
        self, start_register: int = 0, count: int = 1, holding: bool = True
    ) -> Optional[list[int]]:
        """
        Read data from Modbus registers.

        Args:
            start_register (int, optional):
                The starting address of the register(s) to read. Defaults to 0.
            count (int, optional):
                The number of registers to read. Defaults to 1.
            holding (bool, optional):
                If True, reads holding registers; otherwise, reads input registers.
                Defaults to True.

        Returns:
            Union[list[int], None]:
                A list of register values if the read operation is successful. Returns None if an
                error occurs or the response is invalid.
        """
        return await modbus_read_registers(
            self.client,
            start_register=start_register,
            count=count,
            slave=self.address,
            holding=holding,
            logger=self.logger,
        )

    async def read_register(
        self, register: int, holding: bool = True, signed: bool = False
    ) -> Optional[int]:
        """
        Read data from a single Modbus register.

        Args:
            register (int):
                The address of the register to read.
            holding (bool, optional):
                If True, reads from holding registers; otherwise, reads from input registers.
                Defaults to True.
            signed (bool, optional):
                If True, interprets the register value as a signed integer. Defaults to False.

        Returns:
            Optional[int]:
                The register value as an integer. Returns None if an error occurs or the response
                is invalid.
        """
        response: Optional[list[int]] = await self.read_registers(
            register, count=1, holding=holding
        )
        if response:
            if signed:
                return to_signed16(response[0])
            return response[0]
        return None

    async def write_register(
        self, register: int, value: int, signed: bool = False
    ) -> Optional[int]:
        """
        Write data to a single Modbus register.

        Args:
            register (int):
                The address of the register to write to.
            value (int):
                The value to write to the register.
            signed (bool, optional):
                If True, interprets the value as a signed integer. Defaults to False.

        Returns:
            Optional[int]:
                The written register value as an integer. Returns None if an error occurs or the
                response is invalid.
        """
        if signed:
            value = from_signed16(value)

        response = await modbus_write_registers(
            self.client,
            register=register,
            value=[value],
            slave=self.address,
            logger=self.logger,
        )
        if response:
            if signed:
                return to_signed16(response[0])
            return response[0]
        return await self.read_register(register, holding=True, signed=signed)

    async def read_register_float(
        self,
        register: int,
        factor: int = 100,
        signed: bool = False,
        holding: bool = True,
    ) -> Optional[float]:
        """
        Read and parse a float value from a single Modbus register.

        The register value is divided by the provided factor to produce the result.

        Args:
            register (int):
                The address of the register to read.
            factor (int, optional):
                The divisor used to scale the integer value into a float. Defaults to 100.
            signed (bool, optional):
                If True, interprets the register value as a signed integer. Defaults to False.
            holding (bool, optional):
                If True, reads from holding registers; otherwise, reads from input registers.
                Defaults to True.

        Returns:
            Optional[float]:
                The parsed float value. Returns None if an error occurs or the response is invalid.
        """
        response: Optional[int] = await self.read_register(
            register, holding=holding, signed=signed
        )
        if response:
            return float_from_int(response, factor)
        return None

    async def write_register_float(
        self, register: int, value: float, factor: int = 100, signed: bool = False
    ) -> Optional[float]:
        """
        Write a float value to a single Modbus register.

        The float value is multiplied by the provided factor to produce the integer value to write.

        Args:
            register (int):
                The address of the register to write to.
            value (float):
                The float value to write.
            factor (int, optional):
                The multiplier used to scale the float value into an integer. Defaults to 100.
            signed (bool, optional):
                If True, interprets the value as a signed integer. Defaults to False.

        Returns:
            Optional[float]:
                The written float value. Returns None if an error occurs or the response is
                invalid.
        """
        response: Optional[int] = await self.write_register(
            register, float_to_unsigned16(value, factor), signed=False
        )
        if response:
            if signed:
                return float_from_unsigned16(response, factor)
            return float_from_int(response, factor)
        return await self.read_register_float(register, factor, signed=signed)

    async def read_two_registers_int(
        self,
        start_register: int,
        holding: bool = True,
        byteorder: ByteOrder = ByteOrder.LITTLE_ENDIAN,
        signed: bool = False,
    ) -> Optional[int]:
        """
        Read and parse a 32-bit integer value from two Modbus registers.

        Args:
            start_register (int):
                The starting address of the registers to read.
            holding (bool, optional):
                If True, reads from holding registers; otherwise, reads from input registers.
                Defaults to True.
            byteorder (ByteOrder, optional):
                The byte order for combining the two registers.
                Defaults to `ByteOrder.LITTLE_ENDIAN`.
            signed (bool, optional):
                If True, interprets the value as a signed integer. Defaults to False.

        Returns:
            Optional[int]:
                The parsed 32-bit integer value. Returns None if an error occurs or the response
                is invalid.
        """
        response: Optional[list[int]] = await self.read_registers(
            start_register, count=2, holding=holding
        )
        if response and len(response) == 2:
            val = combine_32bit(response[0], response[1], byteorder)
            if signed:
                return to_signed32(val)
            return val
        self.logger.debug("Invalid response: expected 2 registers, got %s", response)
        return None

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    async def read_two_registers_float(
        self,
        start_register: int,
        factor: Union[int, float] = 100,
        holding: bool = True,
        byteorder: ByteOrder = ByteOrder.LITTLE_ENDIAN,
        signed: bool = False,
    ) -> Optional[float]:
        """
        Read and parse a float value from two Modbus registers.

        The integer value read from the registers is divided by the provided factor to produce
        the result.

        Args:
            start_register (int):
                The starting address of the registers to read.
            factor (Union[int, float], optional):
                The divisor used to scale the integer value into a float. Must not be zero.
                Defaults to 100.
            holding (bool, optional):
                If True, reads from holding registers; otherwise, reads from input registers.
                Defaults to True.
            byteorder (ByteOrder, optional):
                The byte order for combining the two registers.
                Defaults to `ByteOrder.LITTLE_ENDIAN`.
            signed (bool, optional):
                If True, interprets the value as a signed integer. Defaults to False.

        Returns:
            Optional[float]:
                The parsed float value. Returns None if an error occurs or the response is invalid.

        Raises:
            ValueError: If `factor` is zero.
        """
        if factor == 0:
            raise ValueError("Factor cannot be zero.")
        response: Optional[int] = await self.read_two_registers_int(
            start_register, holding=holding, byteorder=byteorder, signed=signed
        )
        if response is not None:
            return float_from_int(response, factor)
        self.logger.debug("Failed to read registers for float conversion.")
        return None

    async def write_two_registers(
        self,
        start_register: int,
        value: int,
        byteorder: ByteOrder = ByteOrder.LITTLE_ENDIAN,
        signed: bool = False,
    ) -> Optional[int]:
        """
        Write a 32-bit integer value to two Modbus registers.

        Args:
            start_register (int):
                The starting address of the registers to write to.
            value (int):
                The 32-bit integer value to write.
            byteorder (ByteOrder, optional):
                The byte order for splitting the value into two registers.
                Defaults to `ByteOrder.LITTLE_ENDIAN`.
            signed (bool, optional):
                If True, interprets the value as a signed integer. Defaults to False.

        Returns:
            Optional[int]:
                The written 32-bit integer value. Returns None if an error occurs or the response
                is invalid.
        """
        if signed:
            value = from_signed32(value)
        value_a, value_b = split_32bit(value, byteorder)
        response = await modbus_write_registers(
            self.client,
            register=start_register,
            value=[value_a, value_b],
            slave=self.address,
            logger=self.logger,
        )
        if response and len(response) == 2:
            val = combine_32bit(response[0], response[1], byteorder)
            if signed:
                return to_signed32(val)
            return val
        return await self.read_two_registers_int(
            start_register=start_register,
            holding=True,
            byteorder=byteorder,
            signed=signed,
        )

    async def write_two_registers_float(
        self,
        start_register: int,
        value: float,
        factor: Union[int, float] = 100,
        byteorder: ByteOrder = ByteOrder.LITTLE_ENDIAN,
        signed: bool = False,
    ) -> Optional[float]:
        """
        Write a float value to two Modbus registers.

        The float value is multiplied by the provided factor to produce the integer value to write.

        Args:
            start_register (int):
                The starting address of the registers to write to.
            value (float):
                The float value to write.
            factor (Union[int, float], optional):
                The multiplier used to scale the float value into an integer. Must not be zero.
                Defaults to 100.
            byteorder (ByteOrder, optional):
                The byte order for splitting the value into two registers.
                Defaults to `ByteOrder.LITTLE_ENDIAN`.
            signed (bool, optional):
                If True, interprets the value as a signed integer. Defaults to False.

        Returns:
            Optional[float]:
                The written float value. Returns None if an error occurs or the response is
                invalid.

        Raises:
            ValueError: If `factor` is zero.
        """
        value_int: int = int(round(value * factor))
        response: Optional[int] = await self.write_two_registers(
            start_register, value_int, byteorder, signed
        )
        if response is not None:
            if signed:
                return float_from_unsigned32(response, factor)
            return float_from_int(response, factor)
        return await self.read_two_registers_float(
            start_register, factor, signed=signed
        )

    async def read_data(self) -> dict[str, Union[int, float, list[Union[int, float]]]]:
        """
        Read data from the device and return it as a dictionary.

        This method is intended to be overridden in subclasses to provide device-specific data.

        Returns:
            dict[str, Union[int, float, list[Union[int, float]]]:
                A dictionary containing the data read from the device.
        """
        self.logger.debug("Read data request.")
        return {}

    async def process_message(self, message: dict[str, Any]):
        """
        Process an external message.

        This method is intended to be overridden in subclasses to handle device-specific messages.

        Args:
            message (dict[str, Any]):
                The message to process.
        """
        self.logger.debug("Got message %s.", message)
