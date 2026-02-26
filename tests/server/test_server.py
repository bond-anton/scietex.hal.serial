"""Test RS485Server"""

from logging import Logger

from pymodbus.client import AsyncModbusSerialClient

import pytest

try:
    from src.scietex.hal.serial.utilities.modbus import modbus_connection_config
    from src.scietex.hal.serial.config import (
        ModbusSerialConnectionConfig as Config,
    )
    from src.scietex.hal.serial.server.rs485_server import RS485Server, SERVER_INFO
except ModuleNotFoundError:
    from scietex.hal.serial.utilities.modbus import modbus_connection_config
    from scietex.hal.serial.config import ModbusSerialConnectionConfig as Config
    from scietex.hal.serial.server.rs485_server import RS485Server, SERVER_INFO


@pytest.mark.asyncio
async def test_initialization(
    logger_fixture, single_slave_fixture, store_fixture
):  # pylint: disable=redefined-outer-name
    """Test that the RS485Server initializes correctly."""
    # Test initialization without a logger
    config = Config("COM1", timeout=None)
    server = RS485Server(config, logger=logger_fixture)
    assert server.con_params == config
    assert server.identity.VendorName == SERVER_INFO["VendorName"]
    assert server.identity.VendorUrl == SERVER_INFO["VendorUrl"]
    assert server.identity.ProductName == SERVER_INFO["ProductName"]
    assert server.identity.ModelName == SERVER_INFO["ModelName"]
    assert server.identity.MajorMinorRevision == SERVER_INFO["MajorMinorRevision"]

    # Test initialization with a device_id
    server_with_slave = RS485Server(config, devices=single_slave_fixture)
    assert server_with_slave.devices == single_slave_fixture

    server_with_slave = RS485Server(config, devices={})
    assert server_with_slave.devices == {}
    await server_with_slave.update_slave(1, store_fixture)
    assert server_with_slave.devices == {1: store_fixture}
    await server_with_slave.remove_slave(1)
    assert server_with_slave.devices == {}

    # Test initialization with a logger
    server_with_logger = RS485Server(config, logger=logger_fixture)
    assert isinstance(server_with_logger.logger, Logger)


@pytest.mark.asyncio
async def test_start_stop_restart(
    logger_fixture, server_config
):  # pylint: disable=redefined-outer-name
    """Test that the start(), stop(), and stop() methods work correctly."""

    server = RS485Server(server_config, logger=logger_fixture)

    # pylint: disable=protected-access
    assert server._task is None
    await server.start()
    assert server._task is not None
    assert not server._task.done()

    await server.stop()
    assert server._task is None

    # start_task = asyncio.create_task(server.start())
    await server.start()
    await server.restart()
    assert server._task is not None
    assert not server._task.done()
    await server.stop()
    assert server._task is None


@pytest.mark.asyncio
async def test_update_slaves(
    rs485_srv, store_fixture
):  # pylint: disable=redefined-outer-name
    """Test update devices."""
    await rs485_srv.start()
    await rs485_srv.remove_slave(1)
    assert rs485_srv.devices == {}
    await rs485_srv.update_slave(1, store_fixture)
    assert rs485_srv.devices == {1: store_fixture}
    await rs485_srv.update_slave(2, store_fixture)
    assert rs485_srv.devices == {1: store_fixture, 2: store_fixture}
    await rs485_srv.stop()


@pytest.mark.asyncio
async def test_read_registers(
    rs485_srv, client_config
):  # pylint: disable=redefined-outer-name
    """Test read registers."""
    await rs485_srv.start()
    client = AsyncModbusSerialClient(**modbus_connection_config(client_config))
    await client.connect()
    response = await client.read_discrete_inputs(address=0, count=100, device_id=1)
    assert hasattr(response, "bits")
    assert response.bits[:100] == [1] * 100
    response = await client.read_coils(address=0, count=100, device_id=1)
    assert hasattr(response, "bits")
    assert response.bits[:100] == [0] * 100
    response = await client.read_input_registers(address=0, count=100, device_id=1)
    assert hasattr(response, "registers")
    assert response.registers == list(range(1, 101))
    response = await client.read_holding_registers(address=0, count=100, device_id=1)
    assert hasattr(response, "registers")
    assert response.registers == list(range(1, 101))
    client.close()
    await rs485_srv.stop()


@pytest.mark.asyncio
async def test_write_registers(
    rs485_srv, client_config
):  # pylint: disable=redefined-outer-name
    """Test write registers."""
    await rs485_srv.start()
    client = AsyncModbusSerialClient(**modbus_connection_config(client_config))
    await client.connect()

    response = await client.read_holding_registers(address=0, count=100, device_id=1)
    assert hasattr(response, "registers")
    assert response.registers == list(range(1, 101))

    response = await client.write_registers(address=0, values=[9, 8, 7], device_id=1)
    assert hasattr(response, "registers")

    response = await client.read_holding_registers(address=0, count=3, device_id=1)
    assert hasattr(response, "registers")
    assert response.registers == [9, 8, 7]

    client.close()
    await rs485_srv.stop()


if __name__ == "__main__":
    pytest.main()
