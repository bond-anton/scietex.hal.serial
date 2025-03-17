"""
Modbus basic utility functions.

This module provides essential utility functions for working with the Modbus protocol, specifically
for serial communication. It includes routines for setting up connections, reading and writing
register values, and handling exceptions gracefully. These functions leverage the `pymodbus`
library and aim to simplify interactions with Modbus-compatible devices.

Dependencies:
    - pymodbus: A popular Python library for implementing Modbus clients and servers.

Functions:
    - modbus_connection_config(con_params: SerialConnectionMinimalConfigModel) -> dict:
        Prepares a dictionary of parameters for establishing a Modbus connection over
        a serial interface.
    - modbus_read_registers(con_params: ..., start_register: int = 0, ...)
        -> Union[list[int], None]: Reads data from Modbus holding or input registers.
    - modbus_read_input_registers(con_params: ..., start_register: int = 0, ...)
        -> Optional[list[int]]: Reads data specifically from Modbus input registers.
    - modbus_read_holding_registers(con_params: ..., start_register: int = 0, ...)
        -> Union[list[int], None]: Reads data specifically from Modbus holding registers.
    - modbus_write_registers(con_params: ..., register: int, value: List[int], ...)
        -> Union[list[int], None]: Writes data to Modbus registers.

These functions facilitate robust and efficient Modbus communication, ensuring proper error
handling and adherence to Modbus specifications.

This module simplifies working with Modbus by abstracting low-level details, allowing developers to
focus on higher-level tasks such as retrieving or updating device states.
"""

from typing import Optional, List
import logging
from pymodbus import ModbusException, FramerType
from pymodbus.pdu import ModbusPDU, DecodePDU
from pymodbus.framer import FRAMER_NAME_TO_CLASS, FramerBase
from pymodbus.transaction import TransactionManager
from pymodbus.client import AsyncModbusSerialClient

from ..config import SerialConnectionMinimalConfigModel
from ..config.defaults import DEFAULT_TIMEOUT, DEFAULT_FRAMER


def modbus_connection_config(con_params: SerialConnectionMinimalConfigModel) -> dict:
    """
    Prepare dict for Modbus connection over serial interface.

    This function generates a dictionary containing the necessary parameters for connecting
    to a Modbus device via a serial interface. It validates the input configuration and fills in
    default values for missing fields.

    Args:
        con_params (SerialConnectionMinimalConfigModel): Configuration object specifying serial
            connection settings such as baud rate, parity, etc.

    Returns:
        dict: Dictionary of validated and completed connection parameters.

    Raises:
        TypeError: If the input parameter is not of the expected type.

    Notes:
        - Missing timeout and framer settings are filled with defaults.
        - Supported framer types include ASCII and RTU, mapped to corresponding `FramerType` enums.
    """
    keys: tuple[str, ...] = (
        "port",
        "baudrate",
        "bytesize",
        "stopbits",
        "parity",
        "timeout",
        "framer",
    )
    if not isinstance(con_params, SerialConnectionMinimalConfigModel):
        raise TypeError("Invalid type for Modbus client config.")
    params_dict = con_params.to_dict()
    if "timeout" not in params_dict:
        params_dict["timeout"] = DEFAULT_TIMEOUT
    if "framer" not in params_dict:
        params_dict["framer"] = DEFAULT_FRAMER
    if params_dict["framer"] == "RTU":
        params_dict["framer"] = FramerType.RTU
    elif params_dict["framer"] == "ASCII":
        params_dict["framer"] = FramerType.ASCII
    else:
        ## Fallback framer
        params_dict["framer"] = FramerType.ASCII
    return {k: params_dict[k] for k in keys}


def modbus_get_client(
    con_params: SerialConnectionMinimalConfigModel,
    custom_framer: Optional[type[FramerBase]] = None,
    custom_decoder: Optional[type[DecodePDU]] = None,
    custom_response: Optional[list[type[ModbusPDU]]] = None,
    label: Optional[str] = None,
) -> AsyncModbusSerialClient:
    """
    Creates and configures an asynchronous Modbus serial client with optional customizations.

    This function initializes an `AsyncModbusSerialClient` instance using the provided connection
    parameters. It allows for customization of the framer, decoder, and response handling.
    If no custom components are provided, default implementations are used.

    Args:
        con_params (SerialConnectionMinimalConfigModel):
            A model containing the minimal configuration parameters required for establishing
            a serial connection.
        custom_framer (Optional[type[FramerBase]]):
            An optional custom framer class to be used for framing Modbus messages.
            If not provided, a default framer is selected based on the `framer` parameter
            in `con_params`.
        custom_decoder (Optional[type[DecodePDU]]):
            An optional custom decoder class to be used for decoding Modbus Protocol
            Data Units (PDUs). If not provided, the default `DecodePDU` is used.
        custom_response (Optional[list[type[ModbusPDU]]]):
            An optional list of custom Modbus PDU response types to be registered with the client.
            These are used to handle specific types of Modbus responses.
        label (Optional[str]):
            An optional label for the client. If not provided, the default label "RS485" is used.

    Returns:
        AsyncModbusSerialClient:
            A fully configured asynchronous Modbus serial client instance, ready for communication.
    """
    modbus_params = modbus_connection_config(con_params)
    if label is None:
        label = "RS485"
    client = AsyncModbusSerialClient(name=label, **modbus_params)
    if custom_decoder:
        decoder = custom_decoder(False)
    else:
        decoder = DecodePDU(False)
    if custom_framer:
        framer_instance = custom_framer(decoder)
    else:
        framer_instance = (FRAMER_NAME_TO_CLASS[modbus_params["framer"]])(
            DecodePDU(False)
        )
    client.ctx = TransactionManager(
        client.comm_params,
        framer_instance,
        retries=3,
        is_server=False,
        trace_packet=None,
        trace_pdu=None,
        trace_connect=None,
    )
    if custom_response:
        for custom_response_item in custom_response:
            client.register(custom_response_item)
    return client


async def modbus_execute(
    client: AsyncModbusSerialClient,
    request: ModbusPDU,
    no_response_expected: bool = False,
    logger: Optional[logging.Logger] = None,
):
    """
    Executes a Modbus request asynchronously using the provided client and handles the response.

    This function connects to the Modbus device, sends the request, and processes the response.
    It handles Modbus exceptions and logs errors if a logger is provided. The connection is always
    closed after execution, regardless of success or failure.

    Args:
        client (AsyncModbusSerialClient):
            The asynchronous Modbus serial client used to communicate with the Modbus device.
        request (ModbusPDU):
            The Modbus Protocol Data Unit (PDU) representing the request to be sent to the device.
        no_response_expected (bool, optional):
            If True, indicates that no response is expected from the device. Defaults to False.
        logger (Optional[logging.Logger], optional):
            An optional logger instance for logging errors and exceptions. If not provided,
            no logging is performed.

    Returns:
        Optional[ModbusPDU]:
            The response from the Modbus device as a Modbus PDU. Returns None if an error occurs,
            no response is expected, or if the client fails to connect.

    Raises:
        ModbusException:
            If an error occurs during the execution of the Modbus request.

    Notes:
        - The function ensures that the client connection is closed after execution, even if an
          error occurs.
        - If `no_response_expected` is True, the function will not wait for or process a response
          from the device.
        - Errors and exceptions are logged if a logger is provided.
    """
    await client.connect()
    if not client.connected:
        return None
    try:
        response = await client.execute(no_response_expected, request)
    except ModbusException as e:
        if logger:
            logger.error(
                "%s: Modbus Exception on request execute %s",
                client.comm_params.comm_name,
                e,
            )
        return None
    finally:
        client.close()
    if response.isError():
        if logger:
            logger.error(
                "%s: Received exception from device (%s)",
                client.comm_params.comm_name,
                response,
            )
        return None
    return response


# pylint: disable=too-many-arguments, too-many-positional-arguments
async def modbus_read_registers(
    client: AsyncModbusSerialClient,
    start_register: int = 0,
    count: int = 1,
    slave: int = 1,
    holding: bool = True,
    logger: Optional[logging.Logger] = None,
) -> Optional[list[int]]:
    """
    Reads a sequence of Modbus registers asynchronously using the provided client.

    This function connects to the Modbus device, reads either holding or input registers starting
    from the specified address, and returns the register values. It handles Modbus exceptions and
    logs errors if a logger is provided. The connection is always closed after execution,
    regardless of success or failure.

    Args:
        client (AsyncModbusSerialClient):
            The asynchronous Modbus serial client used to communicate with the Modbus device.
        start_register (int, optional):
            The starting address of the register(s) to read. Defaults to 0.
        count (int, optional):
            The number of registers to read. Defaults to 1.
        slave (int, optional):
            The slave ID of the Modbus device. Defaults to 1.
        holding (bool, optional):
            If True, reads holding registers. If False, reads input registers. Defaults to True.
        logger (logging.Logger, optional):
            An optional logger instance for logging errors and exceptions. If not provided,
            no logging is performed.

    Returns:
        Optional[list[int]]:
            A list of register values if the read operation is successful. Returns None if an
            error occurs, the client fails to connect, or the response does not contain valid
            register data.

    Raises:
        ModbusException:
            If an error occurs during the execution of the Modbus read operation.

    Notes:
        - The function ensures that the client connection is closed after execution, even if an
          error occurs.
        - Errors and exceptions are logged if a logger is provided.
        - The function distinguishes between holding and input registers based on the `holding`
          argument.
    """
    await client.connect()
    if not client.connected:
        return None
    try:
        if holding:
            response = await client.read_holding_registers(
                start_register, count=count, slave=slave
            )
        else:
            response = await client.read_input_registers(
                start_register, count=count, slave=slave
            )
    except ModbusException as e:
        if logger:
            logger.error(
                "%s: Modbus Exception on read input registers %s",
                client.comm_params.comm_name,
                e,
            )
        return None
    finally:
        client.close()
    if response.isError():
        if logger:
            logger.error(
                "%s: Received exception from device (%s)",
                client.comm_params.comm_name,
                response,
            )
        return None
    if hasattr(response, "registers"):
        return response.registers
    return None


# pylint: disable=too-many-arguments, too-many-positional-arguments
async def modbus_read_input_registers(
    client: AsyncModbusSerialClient,
    start_register: int = 0,
    count: int = 1,
    slave: int = 1,
    logger: Optional[logging.Logger] = None,
) -> Optional[list[int]]:
    """
    Reads a sequence of Modbus input registers asynchronously using the provided client.

    This function is a convenience wrapper around `modbus_read_registers` specifically for reading
    input registers. It logs the operation if a logger is provided and delegates the actual reading
    to `modbus_read_registers`.

    Args:
        client (AsyncModbusSerialClient):
            The asynchronous Modbus serial client used to communicate with the Modbus device.
        start_register (int, optional):
            The starting address of the input register(s) to read. Defaults to 0.
        count (int, optional):
            The number of input registers to read. Defaults to 1.
        slave (int, optional):
            The slave ID of the Modbus device. Defaults to 1.
        logger (logging.Logger, optional):
            An optional logger instance for logging debug information and errors. If not provided,
            no logging is performed.

    Returns:
        Optional[list[int]]:
            A list of input register values if the read operation is successful. Returns None if an
            error occurs, the client fails to connect, or the response does not contain valid
            register data.

    Notes:
        - This function specifically reads input registers by setting `holding=False` in the
          underlying `modbus_read_registers` call.
        - Errors and exceptions are logged if a logger is provided.
        - The function ensures that the client connection is closed after execution, even if
          an error occurs.
    """
    if logger:
        logger.debug(
            "%s: Reading input registers, start: %i, count: %i",
            client.comm_params.comm_name,
            start_register,
            count,
        )
    return await modbus_read_registers(
        client,
        start_register,
        count,
        slave,
        holding=False,
        logger=logger,
    )


# pylint: disable=too-many-arguments, too-many-positional-arguments
async def modbus_read_holding_registers(
    client: AsyncModbusSerialClient,
    start_register: int = 0,
    count: int = 1,
    slave: int = 1,
    logger: Optional[logging.Logger] = None,
) -> Optional[list[int]]:
    """
    Reads a sequence of Modbus holding registers asynchronously using the provided client.

    This function is a convenience wrapper around `modbus_read_registers` specifically for reading
    holding registers. It logs the operation if a logger is provided and delegates the actual
    reading to `modbus_read_registers`.

    Args:
        client (AsyncModbusSerialClient):
            The asynchronous Modbus serial client used to communicate with the Modbus device.
        start_register (int, optional):
            The starting address of the holding register(s) to read. Defaults to 0.
        count (int, optional):
            The number of holding registers to read. Defaults to 1.
        slave (int, optional):
            The slave ID of the Modbus device. Defaults to 1.
        logger (logging.Logger, optional):
            An optional logger instance for logging debug information and errors. If not provided,
            no logging is performed.

    Returns:
        Optional[list[int]]:
            A list of holding register values if the read operation is successful. Returns None if
            an error occurs, the client fails to connect, or the response does not contain valid
            register data.

    Notes:
        - This function specifically reads holding registers by setting `holding=True` in the
          underlying `modbus_read_registers` call.
        - Errors and exceptions are logged if a logger is provided.
        - The function ensures that the client connection is closed after execution,
          even if an error occurs.
    """
    if logger:
        logger.debug(
            "%s: Reading holding registers, start: %i, count: %i",
            client.comm_params.comm_name,
            start_register,
            count,
        )
    return await modbus_read_registers(
        client,
        start_register,
        count,
        slave,
        holding=True,
        logger=logger,
    )


# pylint: disable=too-many-arguments, too-many-positional-arguments
async def modbus_write_registers(
    client: AsyncModbusSerialClient,
    register: int,
    value: List[int],
    slave: int = 1,
    logger: Optional[logging.Logger] = None,
) -> Optional[list[int]]:
    """
    Writes a sequence of values to Modbus holding registers asynchronously using the provided
    client.

    This function connects to the Modbus device, writes the provided values to the specified
    holding registers, and handles the response. It logs the operation and any errors if a logger
    is provided. The connection is always closed after execution, regardless of success or failure.

    Args:
        client (AsyncModbusSerialClient):
            The asynchronous Modbus serial client used to communicate with the Modbus device.
        register (int):
            The starting address of the holding register(s) to write to.
        value (List[int]):
            A list of values to write to the holding registers.
        slave (int, optional):
            The slave ID of the Modbus device. Defaults to 1.
        logger (logging.Logger, optional):
            An optional logger instance for logging debug information and errors. If not provided,
            no logging is performed.

    Returns:
        Optional[list[int]]:
            A list of written register values if the write operation is successful. Returns None if
            an error occurs, the client fails to connect, or the response does not contain valid
            register data.

    Raises:
        ModbusException:
            If an error occurs during the execution of the Modbus write operation.

    Notes:
        - The function ensures that the client connection is closed after execution, even if an
          error occurs.
        - Errors and exceptions are logged if a logger is provided.
        - The function writes to holding registers and expects a response containing the written
          values.
    """
    if logger:
        logger.debug(
            "%s: Writing data to registers %i-%i",
            client.comm_params.comm_name,
            register,
            register + len(value),
        )
    await client.connect()
    try:
        response = await client.write_registers(register, value, slave=slave)
    except ModbusException as e:
        if logger:
            logger.error(
                "%s: Modbus Exception on write register %s",
                client.comm_params.comm_name,
                e,
            )
        client.close()
        return None
    client.close()
    if response.isError():
        if logger:
            logger.error(
                "%s: Received exception from device (%s)",
                client.comm_params.comm_name,
                response,
            )
        return None
    if hasattr(response, "registers"):
        return response.registers
    return None
