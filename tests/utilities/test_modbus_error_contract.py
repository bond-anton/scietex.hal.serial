"""Tests for the strict Modbus error contract (``raise_on_error`` / ``ModbusOperationError``)."""

from unittest.mock import AsyncMock, patch

import pytest

try:
    from src.scietex.hal.serial import ModbusOperationError as TopLevelError
    from src.scietex.hal.serial.client import RS485Client
    from src.scietex.hal.serial.config import ModbusSerialConnectionConfig as Config
    from src.scietex.hal.serial.utilities import ModbusOperationError
    from src.scietex.hal.serial.utilities.modbus import (
        modbus_get_client,
        modbus_read_registers,
        modbus_write_register,
        modbus_write_registers,
    )
except ModuleNotFoundError:
    from scietex.hal.serial import ModbusOperationError as TopLevelError
    from scietex.hal.serial.client import RS485Client
    from scietex.hal.serial.config import ModbusSerialConnectionConfig as Config
    from scietex.hal.serial.utilities import ModbusOperationError
    from scietex.hal.serial.utilities.modbus import (
        modbus_get_client,
        modbus_read_registers,
        modbus_write_register,
        modbus_write_registers,
    )


NONEXISTENT_PORT = "/dev/nonexistent_port_xyz"


def _client_config() -> Config:
    """Return a config pointing at a port that does not exist, so connections fail fast."""
    return Config(NONEXISTENT_PORT, timeout=0.5)


def test_modbus_operation_error_importable() -> None:
    """The exception is reachable from ``utilities`` and re-exported at top level."""
    assert TopLevelError is ModbusOperationError
    assert issubclass(ModbusOperationError, Exception)


@pytest.mark.asyncio
async def test_read_returns_none_on_failure_when_raise_on_error_false() -> None:
    """``raise_on_error=False`` restores the legacy behavior: a failed read returns None."""
    client = modbus_get_client(_client_config())
    result = await modbus_read_registers(
        client, start_register=0, count=1, device_id=1, raise_on_error=False
    )
    assert result is None


@pytest.mark.asyncio
async def test_read_raises_on_error_by_default() -> None:
    """A failed read raises ``ModbusOperationError`` by default (no ``raise_on_error`` arg)."""
    client = modbus_get_client(_client_config())
    with pytest.raises(ModbusOperationError):
        await modbus_read_registers(client, start_register=0, count=1, device_id=1)


@pytest.mark.asyncio
async def test_read_raises_on_error_when_enabled() -> None:
    """``raise_on_error=True`` turns the same failure into ``ModbusOperationError``."""
    client = modbus_get_client(_client_config())
    with pytest.raises(ModbusOperationError):
        await modbus_read_registers(
            client, start_register=0, count=1, device_id=1, raise_on_error=True
        )


@pytest.mark.asyncio
async def test_write_no_response_expected_returns_none() -> None:
    """A no-response write is not a failure, even with ``raise_on_error=True``."""
    client = modbus_get_client(_client_config())
    result = await modbus_write_registers(
        client,
        register=0,
        value=[1, 2],
        device_id=1,
        no_response_expected=True,
        raise_on_error=True,
    )
    assert result is None


@pytest.mark.asyncio
async def test_write_register_no_response_expected_returns_none() -> None:
    """Single-register no-response write is not a failure, even with ``raise_on_error=True``."""
    client = modbus_get_client(_client_config())
    result = await modbus_write_register(
        client,
        register=0,
        value=1,
        device_id=1,
        no_response_expected=True,
        raise_on_error=True,
    )
    assert result is None


@pytest.mark.asyncio
async def test_client_write_registers_raises_instead_of_fallback() -> None:
    """``RS485Client.write_registers`` raises instead of falling back to a read."""
    client = RS485Client(_client_config())
    with pytest.raises(ModbusOperationError):
        await client.write_registers(0, [1, 2, 3], raise_on_error=True)


@pytest.mark.asyncio
async def test_client_write_registers_raises_by_default() -> None:
    """``RS485Client.write_registers`` raises on failure by default (no ``raise_on_error`` arg)."""
    client = RS485Client(_client_config())
    with pytest.raises(ModbusOperationError):
        await client.write_registers(0, [1, 2, 3])


@pytest.mark.asyncio
async def test_client_write_registers_returns_none_when_raise_on_error_false() -> None:
    """``raise_on_error=False`` keeps the legacy write->read fallback (returns None)."""
    client = RS485Client(_client_config())
    result = await client.write_registers(0, [1, 2, 3], raise_on_error=False)
    assert result is None


@pytest.mark.asyncio
async def test_client_write_registers_fallback_reads_back_when_raise_on_error_false() -> None:
    """``raise_on_error=False`` fires the write->read fallback and returns the read result."""
    client = RS485Client(_client_config())
    with patch.object(client, "read_registers", new=AsyncMock(return_value=[1, 2, 3])) as mock_read:
        result = await client.write_registers(0, [1, 2, 3], raise_on_error=False)
    assert result == [1, 2, 3]
    mock_read.assert_awaited_once_with(0, count=3, holding=True, signed=False, raise_on_error=False)


@pytest.mark.asyncio
async def test_client_read_success_with_raise_on_error(rs485_srv, client_config):  # pylint: disable=redefined-outer-name
    """``raise_on_error=True`` returns the value on a successful read instead of raising."""
    await rs485_srv.start()
    client = RS485Client(client_config)
    result = await client.read_register(0, raise_on_error=True)
    assert result == 1
    await client.close()
    await rs485_srv.stop()


@pytest.mark.asyncio
async def test_client_write_success_with_raise_on_error(rs485_srv, client_config):  # pylint: disable=redefined-outer-name
    """``raise_on_error=True`` returns the value on a successful write instead of raising."""
    await rs485_srv.start()
    client = RS485Client(client_config)
    result = await client.write_register(0, 7, raise_on_error=True)
    assert result == 7
    await client.close()
    await rs485_srv.stop()


@pytest.mark.asyncio
async def test_modbus_write_register_no_response_expected_connected(rs485_srv, client_config):  # pylint: disable=redefined-outer-name
    """A no-response write against a live server returns None instead of crashing."""
    await rs485_srv.start()
    client = modbus_get_client(client_config)
    result = await modbus_write_register(
        client,
        register=0,
        value=1,
        device_id=1,
        no_response_expected=True,
        raise_on_error=True,
    )
    assert result is None
    await rs485_srv.stop()
