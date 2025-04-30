"""Test modbus utils."""

from logging import Logger
import pytest

try:
    from src.scietex.hal.serial.client import RS485Client
    from src.scietex.hal.serial.utilities.numeric import (
        ByteOrder,
        combine_32bit,
        to_signed32,
    )
except ModuleNotFoundError:
    from scietex.hal.serial.client import RS485Client
    from scietex.hal.serial.utilities.numeric import ByteOrder


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


# pylint: disable=redefined-outer-name
@pytest.mark.asyncio
async def test_client_init(client_config, logger_fixture) -> None:
    """
    Test RS485Client constructor function.
    """
    client = RS485Client(
        client_config, address=2, label="MY DEV", logger=logger_fixture
    )
    assert client.address == 2
    assert client.label == "MY DEV"
    assert client.logger == logger_fixture

    client = RS485Client(client_config)
    assert client.address == 1
    assert client.label == "RS485 Device"
    assert isinstance(client.logger, Logger)


@pytest.mark.asyncio
async def test_read_registers(
    rs485_srv, client_config, logger_fixture
):  # pylint: disable=redefined-outer-name
    """Test reading registers."""
    await rs485_srv.start()
    client = RS485Client(
        client_config, address=1, label="MY DEV", logger=logger_fixture
    )
    value = await client.read_register(register=0, holding=True, signed=False)
    assert value == 1
    value = await client.read_register(register=101, holding=True, signed=False)
    assert value is None
    value = await client.read_register(register=0, holding=False, signed=True)
    assert value == 1
    value = await client.read_register_float(
        register=0, factor=100, holding=False, signed=True
    )
    assert isinstance(value, float)
    assert value == 0.01
    value = await client.read_register_float(
        register=101, factor=100, holding=False, signed=True
    )
    assert value is None
    values = await client.read_registers(start_register=0, count=100, holding=False)
    assert values == list(range(1, 101))
    values = await client.read_registers(start_register=0, count=100, holding=True)
    assert values == list(range(1, 101))
    value = await client.read_two_registers_int(
        start_register=0, holding=False, signed=False, byteorder=ByteOrder.LITTLE_ENDIAN
    )
    assert value == combine_32bit(1, 2, byteorder=ByteOrder.LITTLE_ENDIAN)
    value = await client.read_two_registers_int(
        start_register=0, holding=True, signed=True, byteorder=ByteOrder.BIG_ENDIAN
    )
    assert value == to_signed32(combine_32bit(1, 2, byteorder=ByteOrder.BIG_ENDIAN))
    value = await client.read_two_registers_int(
        start_register=101,
        holding=False,
        signed=False,
        byteorder=ByteOrder.LITTLE_ENDIAN,
    )
    assert value is None
    value = await client.read_two_registers_float(
        start_register=0,
        factor=100,
        holding=True,
        signed=False,
        byteorder=ByteOrder.LITTLE_ENDIAN,
    )
    assert isinstance(value, float)
    assert value == float(combine_32bit(1, 2, byteorder=ByteOrder.LITTLE_ENDIAN)) / 100
    value = await client.read_two_registers_float(
        start_register=0,
        factor=100,
        holding=True,
        signed=True,
        byteorder=ByteOrder.BIG_ENDIAN,
    )
    assert isinstance(value, float)
    assert (
        value
        == float(to_signed32(combine_32bit(1, 2, byteorder=ByteOrder.BIG_ENDIAN))) / 100
    )
    value = await client.read_two_registers_float(
        start_register=101,
        factor=100,
        holding=False,
        signed=False,
        byteorder=ByteOrder.LITTLE_ENDIAN,
    )
    assert value is None
    with pytest.raises(ValueError):
        await client.read_two_registers_float(
            start_register=101,
            factor=0,
            holding=False,
            signed=False,
            byteorder=ByteOrder.LITTLE_ENDIAN,
        )

    await rs485_srv.stop()


@pytest.mark.asyncio
async def test_write_registers(
    rs485_srv, client_config, logger_fixture
):  # pylint: disable=redefined-outer-name
    """Test writing registers."""
    await rs485_srv.start()
    client = RS485Client(client_config, logger=logger_fixture)
    value = await client.write_register(register=0, value=7, signed=False)
    assert value == 7
    value = await client.write_register(register=0, value=-7, signed=True)
    assert value == -7
    value = await client.write_register_float(register=0, value=0.07, signed=False)
    assert value == 0.07
    value = await client.write_register_float(register=0, value=-1.07, signed=True)
    assert value == -1.07
    # Need to check what happens when writing outside the registers range
    # value = await client.write_register_float(register=101, value=-1.07, signed=True)
    # assert value is None
    value = await client.write_two_registers(
        start_register=0, value=1024365, byteorder=ByteOrder.LITTLE_ENDIAN, signed=False
    )
    assert value == 1024365
    value = await client.write_two_registers(
        start_register=0, value=-1024365, byteorder=ByteOrder.BIG_ENDIAN, signed=True
    )
    assert value == -1024365

    value = await client.write_two_registers_float(
        start_register=0, value=0.07, signed=False
    )
    assert value == 0.07
    value = await client.write_two_registers_float(
        start_register=0, value=-10000000.07, signed=True
    )
    assert value == -10000000.07
    # Need to check what happens when writing outside the registers range
    # value = await client.write_two_registers_float(
    #     start_register=101, value=-1.07, signed=True
    # )
    # assert value is None

    values = [1, 2, 3]
    resp = await client.write_registers(0, values, signed=False)
    assert values == resp

    values = [1, 2, -365]
    resp = await client.write_registers(0, values, signed=True)
    assert values == resp

    resp = await client.read_registers(0, 3, signed=True)
    assert values == resp

    await rs485_srv.stop()


if __name__ == "__main__":
    pytest.main()
