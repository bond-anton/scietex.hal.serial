"""Test modbus utils."""

from pymodbus.framer import FramerRTU
from pymodbus.pdu import DecodePDU, ModbusPDU
from pymodbus.client import AsyncModbusSerialClient

import pytest

try:
    from src.scietex.hal.serial.config import (
        SerialConnectionMinimalConfig,
        SerialConnectionConfig,
        ModbusSerialConnectionConfig,
    )
    from src.scietex.hal.serial.config.defaults import (
        DEFAULT_BAUDRATE,
        DEFAULT_BYTESIZE,
        DEFAULT_PARITY,
        DEFAULT_STOPBITS,
        DEFAULT_TIMEOUT,
    )
    from src.scietex.hal.serial.utilities.modbus import (
        FramerType,
        modbus_connection_config,
        modbus_get_client,
        modbus_read_registers,
        modbus_read_input_registers,
        modbus_read_holding_registers,
        modbus_write_registers,
        modbus_write_register,
    )
except ModuleNotFoundError:
    from scietex.hal.serial.config import (
        SerialConnectionMinimalConfig,
        SerialConnectionConfig,
        ModbusSerialConnectionConfig,
    )
    from scietex.hal.serial.config.defaults import (
        DEFAULT_BAUDRATE,
        DEFAULT_BYTESIZE,
        DEFAULT_PARITY,
        DEFAULT_STOPBITS,
        DEFAULT_TIMEOUT,
    )
    from scietex.hal.serial.utilities.modbus import (
        FramerType,
        modbus_connection_config,
        modbus_get_client,
        modbus_read_registers,
        modbus_read_input_registers,
        modbus_read_holding_registers,
        modbus_write_registers,
        modbus_write_register,
    )


# pylint: disable=import-error,unused-import
from tests.fixtures import (
    logger_fixture,
    vsp_fixture,
    store_fixture,
    single_slave_fixture,
    server_config,
    client_config,
    rs485_srv,
)


def test_client_config() -> None:
    """
    Test modbus_client_config function.
    """
    with pytest.raises(TypeError):
        _ = modbus_connection_config("COM1")
    config_min = SerialConnectionMinimalConfig("COM1")
    mb_config = modbus_connection_config(config_min)
    assert mb_config["port"] == "COM1"
    assert mb_config["parity"] == DEFAULT_PARITY
    assert mb_config["baudrate"] == DEFAULT_BAUDRATE
    assert mb_config["bytesize"] == DEFAULT_BYTESIZE
    assert mb_config["stopbits"] == DEFAULT_STOPBITS
    assert mb_config["timeout"] == DEFAULT_TIMEOUT
    assert mb_config["framer"] == FramerType.RTU
    mb_config["framer"] = "ASCII"
    config_mb = ModbusSerialConnectionConfig(**mb_config)
    mb_config = modbus_connection_config(config_mb)
    assert mb_config["framer"] == FramerType.ASCII
    config_serial = SerialConnectionConfig("COM1")
    mb_config = modbus_connection_config(config_serial)
    assert mb_config["port"] == "COM1"
    assert mb_config["parity"] == DEFAULT_PARITY
    assert mb_config["baudrate"] == DEFAULT_BAUDRATE
    assert mb_config["bytesize"] == DEFAULT_BYTESIZE
    assert mb_config["stopbits"] == DEFAULT_STOPBITS
    assert mb_config["timeout"] == DEFAULT_TIMEOUT
    assert mb_config["framer"] == FramerType.RTU


@pytest.mark.asyncio
async def test_get_client(client_config):  # pylint: disable=redefined-outer-name
    """Test modbus_get_client function."""

    client = modbus_get_client(
        client_config,
        custom_framer=FramerRTU,
        custom_decoder=DecodePDU,
        custom_response=[ModbusPDU],
        label="TestDev",
    )
    assert isinstance(client, AsyncModbusSerialClient)
    assert client.comm_params.comm_name == "TestDev"
    for _ in range(2):
        await client.connect()
        assert client.connected
        client.close()
        assert not client.connected


@pytest.mark.asyncio
async def test_read_registers(
    rs485_srv, client_config, logger_fixture, store_fixture, vsp_fixture
):  # pylint: disable=redefined-outer-name
    """Test reading registers."""
    await rs485_srv.start()
    await rs485_srv.update_slave(2, store_fixture)

    client = modbus_get_client(client_config)

    # read input registers
    reg_data = await modbus_read_input_registers(
        client,
        start_register=0,
        count=100,
        device_id=1,
        logger=logger_fixture,
    )
    assert reg_data == list(range(1, 101))
    reg_data = await modbus_read_registers(
        client,
        start_register=0,
        count=100,
        device_id=2,
        logger=logger_fixture,
        holding=False,
    )
    assert reg_data == list(range(1, 101))

    # read holding registers
    reg_data = await modbus_read_holding_registers(
        client,
        start_register=0,
        count=100,
        device_id=1,
        logger=logger_fixture,
    )
    assert reg_data == list(range(1, 101))
    reg_data = await modbus_read_registers(
        client,
        start_register=0,
        count=100,
        device_id=2,
        logger=logger_fixture,
        holding=True,
    )
    assert reg_data == list(range(1, 101))

    # offset 10, wrong count
    # behaves different in pymodbus 3.8 and 3.9
    # reg_data = await modbus_read_holding_registers(
    #     client,
    #     start_register=10,
    #     count=100,
    #     device_id=1,
    #     logger=logger_fixture,
    # )
    # assert reg_data == list(range(11, 101))

    # Stop server
    await rs485_srv.stop()
    reg_data = await modbus_read_holding_registers(
        client,
        start_register=0,
        count=100,
        device_id=1,
        logger=logger_fixture,
    )
    assert reg_data is None

    # Start server
    await rs485_srv.start()
    reg_data = await modbus_read_registers(
        client,
        start_register=0,
        count=100,
        device_id=2,
        logger=logger_fixture,
        holding=False,
    )
    assert reg_data == list(range(1, 101))

    # Stop VSP
    vsp_fixture.stop()
    reg_data = await modbus_read_registers(
        client,
        start_register=0,
        count=100,
        device_id=2,
        logger=logger_fixture,
        holding=False,
    )
    assert reg_data is None

    # Start VSP
    vsp_fixture.start()
    await rs485_srv.restart()
    reg_data = await modbus_read_registers(
        client,
        start_register=0,
        count=100,
        device_id=1,
        logger=logger_fixture,
        holding=False,
    )
    assert reg_data == list(range(1, 101))

    await rs485_srv.stop()


@pytest.mark.asyncio
async def test_write_registers(
    rs485_srv, client_config, logger_fixture
):  # pylint: disable=redefined-outer-name
    """Test writing registers."""
    await rs485_srv.start()
    client = modbus_get_client(client_config)

    reg_data = await modbus_read_holding_registers(
        client,
        start_register=0,
        count=100,
        device_id=1,
        logger=logger_fixture,
    )
    assert reg_data == list(range(1, 101))

    await modbus_write_registers(
        client,
        register=0,
        value=[7, 8, 9],
        device_id=1,
        logger=logger_fixture,
    )
    reg_data = await modbus_read_holding_registers(
        client,
        start_register=0,
        count=100,
        device_id=1,
        logger=logger_fixture,
    )
    assert reg_data[:4] == [7, 8, 9, 4]

    reg_data = await modbus_write_registers(
        client,
        register=0,
        value=[100, 101],
        device_id=10,
        logger=logger_fixture,
    )
    assert reg_data is None

    await rs485_srv.stop()


@pytest.mark.asyncio
async def test_write_register(
    rs485_srv, client_config, logger_fixture
):  # pylint: disable=redefined-outer-name
    """Test writing single register."""
    await rs485_srv.start()
    client = modbus_get_client(client_config)

    reg_data = await modbus_read_holding_registers(
        client,
        start_register=0,
        count=1,
        device_id=1,
        logger=logger_fixture,
    )
    assert reg_data == [1]

    await modbus_write_register(
        client,
        register=0,
        value=7,
        device_id=1,
        logger=logger_fixture,
    )
    reg_data = await modbus_read_holding_registers(
        client,
        start_register=0,
        count=1,
        device_id=1,
        logger=logger_fixture,
    )
    assert reg_data[0] == 7

    reg_data = await modbus_write_register(
        client,
        register=0,
        value=100,
        device_id=10,
        logger=logger_fixture,
    )
    assert reg_data is None

    await rs485_srv.stop()


if __name__ == "__main__":
    pytest.main()
