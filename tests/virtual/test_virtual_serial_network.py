"""Test Virtual Serial Network module"""

import os
from logging import Logger

import pytest

try:
    from src.scietex.hal.serial.utilities.mock import mock_openpty
    from src.scietex.hal.serial.config import SerialConnectionConfig
    from src.scietex.hal.serial.virtual.virtual_serial_network import (
        VirtualSerialNetwork,
    )
except ModuleNotFoundError:
    from scietex.hal.serial.utilities.mock import mock_openpty
    from scietex.hal.serial.config import SerialConnectionConfig
    from scietex.hal.serial.virtual.virtual_serial_network import (
        VirtualSerialNetwork,
    )

# pylint: disable=import-error,unused-import
from tests.fixtures import logger_fixture, vsn_fixture


def test_initialization(logger_fixture):  # pylint: disable=redefined-outer-name
    """Test that the VirtualSerialNetwork initializes correctly."""
    # Test initialization without a logger
    vsn = VirtualSerialNetwork()
    # pylint: disable=protected-access
    assert vsn._VirtualSerialNetwork__master_io is None
    assert vsn._VirtualSerialNetwork__worker_io is None
    assert vsn._VirtualSerialNetwork__p is None
    assert vsn.serial_ports == []

    # Test initialization with a logger
    vsn_with_logger = VirtualSerialNetwork(logger=logger_fixture)
    assert isinstance(vsn_with_logger.logger, Logger)


def test_start_stop(vsn_fixture):  # pylint: disable=redefined-outer-name
    """Test that the start() and stop() methods work correctly."""
    virtual_ports_num = 3
    # Verify that serial ports are created
    assert vsn_fixture.virtual_ports_num == virtual_ports_num
    for i in range(virtual_ports_num):
        assert vsn_fixture.serial_ports[i] is not None
        assert os.path.exists(vsn_fixture.serial_ports[i])

    # Verify that the process is running
    # pylint: disable=protected-access
    assert vsn_fixture._VirtualSerialNetwork__p is not None
    assert vsn_fixture._VirtualSerialNetwork__p.is_alive()

    # Stop the process
    vsn_fixture.stop()

    # Verify that resources are cleaned up
    # pylint: disable=protected-access
    assert vsn_fixture._VirtualSerialNetwork__p is None
    assert vsn_fixture.serial_ports == []


# pylint: disable=redefined-outer-name
def test_vsn_init_external_ports(vsn_fixture, logger_fixture):
    """Initialization with external ports list."""
    external_ports = [SerialConnectionConfig(port=vsn_fixture.serial_ports[0])]

    virtual_ports_num = 3
    vsn2 = VirtualSerialNetwork(
        virtual_ports_num=virtual_ports_num,
        external_ports=external_ports * 3
        + [SerialConnectionConfig(port="/dev/not_existing_serial_port_001")],
        loopback=False,
        logger=logger_fixture,
    )
    vsn2.start()
    assert vsn2.external_ports == external_ports

    vsn2.stop()


# pylint: disable=redefined-outer-name
def test_vsn_add_external_ports(vsn_fixture, logger_fixture):
    """Initialization with external ports list."""
    external_ports = [SerialConnectionConfig(port=vsn_fixture.serial_ports[0])]

    virtual_ports_num = 3
    vsn2 = VirtualSerialNetwork(
        virtual_ports_num=virtual_ports_num,
        external_ports=None,
        loopback=False,
        logger=logger_fixture,
    )
    vsn2.add(external_ports)
    assert vsn2.external_ports == []

    vsn2.start()
    assert vsn2.external_ports == []

    vsn2.add(
        external_ports * 2
        + [SerialConnectionConfig(port="/dev/not_existing_serial_port_001")]
    )
    assert vsn2.external_ports == external_ports

    vsn2.add(external_ports)
    assert vsn2.external_ports == external_ports

    vsn2.stop()


# pylint: disable=redefined-outer-name
def test_vsn_remove_ports(vsn_fixture, logger_fixture):
    """Initialization with external ports list."""
    external_port = vsn_fixture.serial_ports[0]
    external_ports = [SerialConnectionConfig(port=external_port)]

    virtual_ports_num = 3
    vsn2 = VirtualSerialNetwork(
        virtual_ports_num=virtual_ports_num,
        external_ports=None,
        loopback=False,
        logger=logger_fixture,
    )
    assert vsn2.virtual_ports_num == 3

    vsn2.start()
    virtual_port = vsn2.serial_ports[0]
    assert virtual_port in vsn2.serial_ports
    assert vsn2.external_ports == []

    vsn2.add(
        external_ports * 2
        + [SerialConnectionConfig(port="/dev/not_existing_serial_port_001")]
    )
    assert vsn2.external_ports == external_ports
    assert len(vsn2.serial_ports) == 4

    vsn2.remove([virtual_port, "/dev/not_existing_serial_port_001"])
    assert vsn2.virtual_ports_num == 2
    assert virtual_port not in vsn2.serial_ports
    assert len(vsn2.serial_ports) == 3

    vsn2.remove([external_port])
    assert vsn2.virtual_ports_num == 2
    assert external_port not in vsn2.serial_ports
    assert len(vsn2.serial_ports) == 2

    vsn2.stop()


def test_create_virtual_ports(vsn_fixture):  # pylint: disable=redefined-outer-name
    """Test creation of additional virtual ports in the network."""
    assert vsn_fixture.virtual_ports_num == 3
    vsn_fixture.create(1)
    assert vsn_fixture.virtual_ports_num == 4
    vsn_fixture.create(3)
    assert vsn_fixture.virtual_ports_num == 7
    vsn_fixture.create(0)
    assert vsn_fixture.virtual_ports_num == 7
    assert len(vsn_fixture.serial_ports) == vsn_fixture.virtual_ports_num
    vsn_fixture.create(-1)
    assert vsn_fixture.virtual_ports_num == 7
    assert len(vsn_fixture.serial_ports) == vsn_fixture.virtual_ports_num


def test_communication(logger_fixture):  # pylint: disable=redefined-outer-name
    """Test that payload can be sent and received between the virtual serial ports."""
    vsn = VirtualSerialNetwork(virtual_ports_num=3, logger=logger_fixture)
    vsn.start()

    try:
        # Open the first serial port for writing
        with open(vsn.serial_ports[0], "wb", buffering=0) as port1:
            # Open the second serial port for reading
            with open(vsn.serial_ports[1], "rb", buffering=0) as port2:
                # Open the third serial port for reading
                with open(vsn.serial_ports[2], "rb", buffering=0) as port3:
                    # Send payload from port1
                    test_data = b"Hello, World!"
                    port1.write(test_data)

                    # Read payload from port2
                    received_data = port2.read(len(test_data))
                    assert received_data == test_data
                    # Read payload from port3
                    received_data = port3.read(len(test_data))
                    assert received_data == test_data
    finally:
        vsn.stop()


# pylint: disable=redefined-outer-name
def test_communication_external_ports(vsn_fixture, logger_fixture):
    """Connect two virtual networks and test communication."""
    virtual_ports_num = 3
    connection_port = vsn_fixture.serial_ports[0]
    external_ports = [SerialConnectionConfig(port=connection_port)]
    vsn = VirtualSerialNetwork(
        virtual_ports_num=virtual_ports_num,
        external_ports=external_ports,
        loopback=False,
        logger=logger_fixture,
    )
    vsn.start()
    free_ports = list(set(vsn.serial_ports) - {connection_port})
    try:
        # Open the first serial port for writing
        with open(free_ports[0], "wb", buffering=0) as port1:
            # Open the second serial port for reading
            with open(free_ports[1], "rb", buffering=0) as port2:
                # Open the third serial port for reading
                with open(vsn_fixture.serial_ports[1], "rb", buffering=0) as port3:
                    # Send payload from port1
                    test_data = b"Hello, World!"
                    port1.write(test_data)
                    # Read payload from port2
                    received_data = port2.read(len(test_data))
                    assert received_data == test_data
                    # Read payload from port3
                    received_data = port3.read(len(test_data))
                    assert received_data == test_data
    finally:
        vsn.stop()


def test_error_handling(logger_fixture):  # pylint: disable=redefined-outer-name
    """Test that errors during pseudo-terminal creation are handled gracefully."""
    vsn = VirtualSerialNetwork(virtual_ports_num=3, logger=logger_fixture)
    assert vsn.virtual_ports_num == 3

    vsn.start(openpty_func=mock_openpty)

    assert vsn.virtual_ports_num == 0
    assert vsn.serial_ports == []

    # pylint: disable=protected-access
    assert vsn._VirtualSerialNetwork__p is not None
    assert vsn._VirtualSerialNetwork__p.is_alive()

    vsn.stop()
    # Ensure that resources are cleaned up after the error
    # pylint: disable=protected-access
    assert vsn._VirtualSerialNetwork__p is None
    assert vsn._VirtualSerialNetwork__master_io is None
    assert vsn._VirtualSerialNetwork__worker_io is None


if __name__ == "__main__":
    pytest.main()
