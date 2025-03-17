"""Test Virtual Serial Pair module"""

import threading
import time
from multiprocessing import Pipe

import pytest


try:
    from src.scietex.hal.serial.utilities.mock import mock_openpty
    from src.scietex.hal.serial.virtual.worker import create_serial_network
except ModuleNotFoundError:
    from scietex.hal.serial.utilities.mock import mock_openpty
    from scietex.hal.serial.virtual.worker import create_serial_network


# pylint: disable=import-error,unused-import
from tests.fixtures import logger_fixture


def test_generate_serial_pair():
    """Test that generate_serial_pair creates a pair of serial ports."""
    parent_conn, child_conn = Pipe()

    # Run generate_serial_pair in a thread
    thread = threading.Thread(
        target=create_serial_network,
        args=(child_conn, 2, None, False),
    )
    thread.start()

    # Receive the serial port names from the thread
    response = parent_conn.recv()
    assert response["status"] == "OK"
    serial_port_1 = response["data"]
    response = parent_conn.recv()
    assert response["status"] == "OK"
    serial_port_2 = response["data"]

    # Verify that the serial ports were created
    assert serial_port_1
    assert serial_port_2

    parent_conn.send("wrong message type")
    response = parent_conn.recv()
    assert response["status"] == "ERROR"

    parent_conn.send({"cmd": "remove", "data": [serial_port_1]})
    response = parent_conn.recv()
    assert response["status"] == "OK"
    assert serial_port_1 == response["data"]

    parent_conn.send({"cmd": "remove", "data": [serial_port_1]})
    response = parent_conn.recv()
    assert response["status"] == "NOT_EXIST"
    assert serial_port_1 == response["data"]

    parent_conn.send({"cmd": "create", "data": 1})
    response = parent_conn.recv()
    assert response["status"] == "OK"
    serial_port_1 = response["data"]

    parent_conn.send({"cmd": "add", "data": [{"port": serial_port_1}]})
    response = parent_conn.recv()
    assert response["status"] == "EXIST"

    parent_conn.send({"cmd": "add", "data": [{"port": "/dev/unknown_serial_port_1"}]})
    response = parent_conn.recv()
    assert response["status"] == "ERROR"

    # Send a stop signal to the thread
    parent_conn.send({"cmd": "STOP"})
    thread.join()


def test_generate_serial_pair_with_error():
    """Test that generate_serial_pair handles errors gracefully."""

    num_ports = 3
    parent_conn, child_conn = Pipe()

    # Run generate_serial_pair in a thread with the mock function
    thread = threading.Thread(
        target=create_serial_network,
        args=(child_conn, num_ports, None, False, mock_openpty),
    )
    thread.start()

    for _ in range(num_ports):
        # Receive the error from the thread
        response = parent_conn.recv()
        assert response["status"] == "ERROR"
        assert response["data"]["error"] == "Failed to create pseudo-terminal"

    parent_conn.send({"cmd": "STOP"})
    thread.join()


def test_communication_thread():
    """Test that data can be sent and received between the virtual serial ports.
    Run generate_serial_pair in a thread for coverage purpose."""
    parent_conn, child_conn = Pipe()
    serial_ports = [None, None, None]

    thread = threading.Thread(
        target=create_serial_network, args=(child_conn, 3, None, False)
    )
    thread.start()

    for i in range(3):
        response = parent_conn.recv()
        serial_ports[i] = response["data"]

    parent_conn2, child_conn2 = Pipe()
    serial_ports2 = [None, None]

    thread2 = threading.Thread(
        target=create_serial_network, args=(child_conn2, 2, None, False)
    )
    thread2.start()

    for i in range(2):
        response = parent_conn2.recv()
        serial_ports2[i] = response["data"]

    parent_conn2.send({"cmd": "add", "data": [{"port": serial_ports[2]}]})
    response = parent_conn2.recv()
    assert response["status"] == "OK"

    # Open the first serial port for writing
    with open(serial_ports[0], "wb", buffering=0) as port1:
        # Open the second serial port for reading
        with open(serial_ports[1], "rb", buffering=0) as port2:
            # Open the second serial port for reading
            with open(serial_ports2[0], "rb", buffering=0) as port3:
                # Send data from port1
                test_data = b"Hello, World!"
                port1.write(test_data)

                # Read data from port2
                received_data = port2.read(len(test_data))
                assert received_data == test_data
                time.sleep(0.1)
                # Read data from port3
                received_data = port3.read(len(test_data))
                assert received_data == test_data

    # Send a stop signal to the thread
    parent_conn.send({"cmd": "STOP"})
    thread.join()

    parent_conn2.send({"cmd": "stop"})
    thread2.join()


if __name__ == "__main__":
    pytest.main()
