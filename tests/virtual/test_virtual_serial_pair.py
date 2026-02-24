"""Test Virtual Serial Pair module"""

import os
from logging import Logger

import pytest

try:
    from src.scietex.hal.serial.utilities.mock import mock_openpty
    from src.scietex.hal.serial.config import SerialConnectionMinimalConfig
    from src.scietex.hal.serial.virtual.virtual_serial_pair import (
        VirtualSerialPair,
    )
except ModuleNotFoundError:
    from scietex.hal.serial.utilities.mock import mock_openpty
    from scietex.hal.serial.config import SerialConnectionMinimalConfig
    from scietex.hal.serial.virtual.virtual_serial_pair import VirtualSerialPair

# pylint: disable=import-error,unused-import
from tests.fixtures import logger_fixture


def test_initialization(logger_fixture):  # pylint: disable=redefined-outer-name
    """Test that the VirtualSerialPair initializes correctly."""
    # Test initialization without a logger
    vsp = VirtualSerialPair()
    # pylint: disable=protected-access
    assert vsp._VirtualSerialNetwork__master_io is None
    assert vsp._VirtualSerialNetwork__worker_io is None
    assert vsp._VirtualSerialNetwork__p is None
    assert vsp.serial_ports == []

    # Test initialization with a logger
    vsp_with_logger = VirtualSerialPair(logger=logger_fixture)
    assert isinstance(vsp_with_logger.logger, Logger)


def test_start_stop(logger_fixture):  # pylint: disable=redefined-outer-name
    """Test that the start() and stop() methods work correctly."""
    vsp = VirtualSerialPair(logger=logger_fixture)
    vsp.start()

    # Verify that serial ports are created
    assert vsp.serial_ports[0] is not None
    assert vsp.serial_ports[1] is not None
    assert os.path.exists(vsp.serial_ports[0])
    assert os.path.exists(vsp.serial_ports[1])

    # Verify that the process is running
    # pylint: disable=protected-access
    assert vsp._VirtualSerialNetwork__p is not None
    assert vsp._VirtualSerialNetwork__p.is_alive()

    vsp.remove([vsp.serial_ports[0]])
    assert vsp.virtual_ports_num == 2

    vsp.create(3)
    assert vsp.virtual_ports_num == 2

    vsp.add([SerialConnectionMinimalConfig(port="/dev/some_port")])
    assert vsp.virtual_ports_num == 2

    # Stop the process
    vsp.stop()

    # Verify that resources are cleaned up
    # pylint: disable=protected-access
    assert vsp._VirtualSerialNetwork__p is None
    assert vsp.serial_ports == []


def test_communication(logger_fixture):  # pylint: disable=redefined-outer-name
    """Test that payload can be sent and received between the virtual serial ports."""
    vsp = VirtualSerialPair(logger=logger_fixture)
    vsp.start()

    try:
        # Open the first serial port for writing
        with open(vsp.serial_ports[0], "wb", buffering=0) as port1:
            # Open the second serial port for reading
            with open(vsp.serial_ports[1], "rb", buffering=0) as port2:
                # Send payload from port1
                test_data = b"Hello, World!"
                port1.write(test_data)

                # Read payload from port2
                received_data = port2.read(len(test_data))
                assert received_data == test_data
    finally:
        vsp.stop()


def test_error_handling(logger_fixture):  # pylint: disable=redefined-outer-name
    """Test that errors during pseudo-terminal creation are handled gracefully."""
    vsp = VirtualSerialPair(logger=logger_fixture)
    assert vsp.virtual_ports_num == 2

    vsp.start(openpty_func=mock_openpty)

    assert vsp.virtual_ports_num == 0
    assert vsp.serial_ports == []

    # Ensure that resources are cleaned up after the error
    # pylint: disable=protected-access
    assert vsp._VirtualSerialNetwork__p is None
    assert vsp._VirtualSerialNetwork__master_io is None
    assert vsp._VirtualSerialNetwork__worker_io is None


if __name__ == "__main__":
    pytest.main()
