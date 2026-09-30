"""Test RS485Client lifecycle (close and async context manager)."""

import pytest

try:
    from src.scietex.hal.serial.client import RS485Client
except ModuleNotFoundError:
    from scietex.hal.serial.client import RS485Client


@pytest.mark.asyncio
async def test_async_context_manager(client_config, logger_fixture) -> None:
    """Test that the client works as an async context manager and closes on exit."""
    async with RS485Client(client_config, logger=logger_fixture) as client:
        assert isinstance(client, RS485Client)
    assert not client.client.connected


@pytest.mark.asyncio
async def test_close_does_not_raise(client_config, logger_fixture) -> None:
    """Test that calling close directly does not raise."""
    client = RS485Client(client_config, logger=logger_fixture)
    await client.close()
    assert not client.client.connected
