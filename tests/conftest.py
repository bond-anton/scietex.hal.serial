"""Fixtures for testing."""

from logging import getLogger

from pymodbus.datastore import ModbusDeviceContext

import pytest

try:
    from src.scietex.hal.serial.virtual import (
        VirtualSerialNetwork,
        VirtualSerialPair,
    )
    from src.scietex.hal.serial.config import (
        ModbusSerialConnectionConfig as Config,
    )
    from src.scietex.hal.serial.server.rs485_server import (
        RS485Server,
        ReactiveSequentialDataBlock,
    )
except ModuleNotFoundError:
    from scietex.hal.serial.virtual import VirtualSerialPair
    from scietex.hal.serial.config import ModbusSerialConnectionConfig as Config
    from scietex.hal.serial.server.rs485_server import (
        RS485Server,
        ReactiveSequentialDataBlock,
    )


# pylint: disable=redefined-outer-name


@pytest.fixture
def logger_fixture():
    """Set up the test environment."""
    logger = getLogger()
    logger.setLevel("DEBUG")
    yield logger


@pytest.fixture
def store_fixture():
    """Slave context."""
    block = ReactiveSequentialDataBlock(0x01, list(range(1, 101)))
    di_block = ReactiveSequentialDataBlock(0x01, list([1] * 100))
    co_block = ReactiveSequentialDataBlock(0x01, list([0] * 100))
    store = ModbusDeviceContext(di=di_block, co=co_block, hr=block, ir=block)
    return store


@pytest.fixture
def single_slave_fixture(store_fixture):
    """Slaves dict."""
    return {0x01: store_fixture}


@pytest.fixture
def vsp_fixture(logger_fixture):
    """Start Virtual Serial Pair."""
    vsp = VirtualSerialPair(logger=logger_fixture)
    vsp.start()
    yield vsp
    vsp.stop()


@pytest.fixture
def vsn_fixture(logger_fixture):
    """Start Virtual Serial Network."""
    virtual_ports_num = 3
    vsn = VirtualSerialNetwork(
        virtual_ports_num=virtual_ports_num,
        external_ports=None,
        loopback=False,
        logger=logger_fixture,
    )
    vsn.start()
    yield vsn
    vsn.stop()


@pytest.fixture
def server_config(vsp_fixture):
    """Serial Modbus config for the server."""
    config = Config(vsp_fixture.serial_ports[0], timeout=0.5)
    return config


@pytest.fixture
def client_config(vsp_fixture):
    """Serial Modbus config for the server."""
    config = Config(vsp_fixture.serial_ports[1], timeout=0.5)
    return config


@pytest.fixture
def rs485_srv(logger_fixture, server_config, single_slave_fixture):
    """RS485 Server."""
    server = RS485Server(
        server_config, devices=single_slave_fixture, logger=logger_fixture
    )
    return server
