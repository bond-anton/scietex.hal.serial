"""Tests for ``RS485Client.connection`` connection reuse."""

import pytest

try:
    from src.scietex.hal.serial.client import RS485Client
except ModuleNotFoundError:
    from scietex.hal.serial.client import RS485Client


@pytest.mark.asyncio
async def test_connection_reuse_ux_target(rs485_srv, client_config):
    """The UX target: one-shot reads, a reuse block, then one-shot reads again."""
    await rs485_srv.start()
    async with RS485Client(client_config, address=1) as client:
        values = await client.read_registers(0, 10)
        assert values == list(range(1, 11))
        assert client._manage_connection is True
        assert not client.client.connected

        async with client.connection():
            assert client._manage_connection is False
            assert client.client.connected
            a = await client.read_registers(0, 10)
            b = await client.read_registers(10, 10)
            await client.write_register(20, 1234)
            assert a == list(range(1, 11))
            assert b == list(range(11, 21))

        assert client._manage_connection is True
        assert not client.client.connected
        c = await client.read_registers(30, 10)
        assert c == list(range(31, 41))
    assert not client.client.connected
    await rs485_srv.stop()


@pytest.mark.asyncio
async def test_connection_closes_on_exception_and_resets(rs485_srv, client_config):
    """``connection()`` closes on exception and restores ``_manage_connection``."""
    await rs485_srv.start()
    client = RS485Client(client_config, address=1)
    assert client._manage_connection is True
    with pytest.raises(RuntimeError):
        async with client.connection():
            assert client._manage_connection is False
            assert client.client.connected
            raise RuntimeError("boom")
    assert client._manage_connection is True
    assert not client.client.connected
    await client.close()
    await rs485_srv.stop()
