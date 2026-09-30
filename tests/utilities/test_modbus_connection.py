"""Tests for the ``modbus_connection`` connection-reuse context manager."""

from unittest.mock import patch

import pytest

try:
    from src.scietex.hal.serial.utilities.modbus import (
        modbus_connection,
        modbus_get_client,
        modbus_read_holding_registers,
        modbus_read_input_registers,
        modbus_read_registers,
        modbus_write_register,
    )
except ModuleNotFoundError:
    from scietex.hal.serial.utilities.modbus import (
        modbus_connection,
        modbus_get_client,
        modbus_read_holding_registers,
        modbus_read_input_registers,
        modbus_read_registers,
        modbus_write_register,
    )


@pytest.mark.asyncio
async def test_reuse_connects_once_closes_once(rs485_srv, client_config):
    """A reuse block connects once and closes once across two managed reads."""
    await rs485_srv.start()
    client = modbus_get_client(client_config)
    with (
        patch.object(client, "connect", wraps=client.connect) as mock_connect,
        patch.object(client, "close", wraps=client.close) as mock_close,
    ):
        async with modbus_connection(client):
            first = await modbus_read_registers(
                client, start_register=0, count=10, manage_connection=False
            )
            second = await modbus_read_registers(
                client, start_register=10, count=10, manage_connection=False
            )
    assert first == list(range(1, 11))
    assert second == list(range(11, 21))
    assert mock_connect.call_count == 1
    assert mock_close.call_count == 1
    assert not client.connected
    await rs485_srv.stop()


@pytest.mark.asyncio
async def test_exception_inside_block_closes(client_config):
    """An exception inside the block still closes the connection."""
    client = modbus_get_client(client_config)
    with patch.object(client, "close", wraps=client.close) as mock_close:
        with pytest.raises(RuntimeError):
            async with modbus_connection(client):
                raise RuntimeError("boom")
    assert mock_close.call_count == 1
    assert not client.connected


@pytest.mark.asyncio
async def test_write_register_does_not_close_socket(rs485_srv, client_config):
    """A managed write followed by a managed read proves the socket stays open."""
    await rs485_srv.start()
    client = modbus_get_client(client_config)
    async with modbus_connection(client):
        await modbus_write_register(client, register=0, value=1234, manage_connection=False)
        reg_data = await modbus_read_registers(
            client, start_register=0, count=1, manage_connection=False
        )
    assert reg_data == [1234]
    assert not client.connected
    await rs485_srv.stop()


@pytest.mark.asyncio
async def test_default_unchanged(rs485_srv, client_config):
    """Without the flag, a read connects and closes per operation."""
    await rs485_srv.start()
    client = modbus_get_client(client_config)
    reg_data = await modbus_read_registers(client, start_register=0, count=10)
    assert reg_data == list(range(1, 11))
    assert not client.connected
    await rs485_srv.stop()


@pytest.mark.asyncio
async def test_delegating_wrappers_forward_flag(rs485_srv, client_config):
    """Input/holding wrappers forward ``manage_connection`` inside a reuse block."""
    await rs485_srv.start()
    client = modbus_get_client(client_config)
    async with modbus_connection(client):
        input_data = await modbus_read_input_registers(
            client, start_register=0, count=10, manage_connection=False
        )
        holding_data = await modbus_read_holding_registers(
            client, start_register=0, count=10, manage_connection=False
        )
    assert input_data == list(range(1, 11))
    assert holding_data == list(range(1, 11))
    assert not client.connected
    await rs485_srv.stop()
