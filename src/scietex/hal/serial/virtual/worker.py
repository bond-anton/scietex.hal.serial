"""
Worker function for serial network creation and management.

This module handles the generation, addition, removal, and data forwarding for virtual and physical
serial ports. It provides functions to manage a virtual network of serial devices, ensuring proper
handling of incoming commands and data exchange between connected ports.

Functions:
    - generate_virtual_ports(stack, selector, ports_number, master_files, slave_names,
        worker_io, openpty_func=None):
        Generates a specified number of virtual serial ports using the provided openpty function.
    - add_external_ports(stack, selector, external_ports, master_files, slave_names, worker_io):
        Adds external serial ports to the virtual network.
    - remove_ports(selector, remove_list, master_files, slave_names, worker_io):
        Removes specified ports from the virtual network.
    - forward_data(selector, master_files, loopback=False):
        Forwards data between connected ports in the virtual network.
    - process_cmd(stack, selector, master_files, slave_names, worker_io, openpty_func=None):
        Processes incoming commands from the worker I/O connection.
    - create_serial_network(worker_io, ports_number=2, external_ports=None,
        loopback=False, openpty_func=pty.openpty):
        Creates a virtual network of serial ports and manages data flow between them.

Raises:
    Various exceptions may occur during port operations, such as IOErrors or configuration errors.
    The exceptions are caught and handled gracefully, ensuring the stability of the virtual network.

This module enables developers to simulate and test complex serial device interactions without
relying on physical hardware, making it ideal for testing and debugging scenarios.
"""

from typing import List, Optional, Union, Callable, BinaryIO
import os
import pty
import tty
from contextlib import ExitStack
from multiprocessing.connection import Connection
import traceback
from selectors import EVENT_READ
from selectors import DefaultSelector as Selector
from serial import Serial  # type: ignore


# pylint: disable=too-many-arguments, too-many-positional-arguments
def generate_virtual_ports(
    stack: ExitStack,
    selector: Selector,
    ports_number: int,
    master_files: dict,
    slave_names: dict,
    worker_io: Connection,
    openpty_func: Optional[Callable] = None,
):
    """
    Generate `ports_number` virtual ports using openpty_func.

    This function creates the specified number of virtual serial ports using the provided openpty
    function. Each created port is registered with the selector and added to the master files and
    slave names dictionaries.

    Args:
        stack (ExitStack): Context manager for resource cleanup.
        selector (Selector): Selector instance for event monitoring.
        ports_number (int): Number of virtual ports to generate.
        master_files (dict): Dictionary mapping master file descriptors to their corresponding
            objects.
        slave_names (dict): Dictionary mapping slave names to their associated master file
            descriptors.
        worker_io (Connection): Worker I/O connection for communicating status updates.
        openpty_func (Optional[Callable], optional): Function to open pseudo-terminal pairs.
            Defaults to pty.openpty.

    Raises:
        SerialConnectionConfigError: If an error occurs during port creation.
    """
    openpty_func = openpty_func if callable(openpty_func) else pty.openpty
    for _ in range(ports_number):
        try:
            master_fd, slave_fd = openpty_func()
            tty.setraw(master_fd)
            os.set_blocking(master_fd, False)
            slave_name = os.ttyname(slave_fd)
            # pylint: disable=consider-using-with
            master_files[master_fd] = open(master_fd, "r+b", buffering=0)
            slave_names[slave_name] = master_fd
            stack.enter_context(master_files[master_fd])
            selector.register(master_fd, EVENT_READ)
            worker_io.send({"status": "OK", "data": slave_name})
        # pylint: disable=broad-exception-caught
        except Exception as e:
            worker_io.send(
                {
                    "status": "ERROR",
                    "data": {"error": str(e), "traceback": traceback.format_exc()},
                }
            )


# pylint: disable=too-many-positional-arguments
def add_external_ports(
    stack: ExitStack,
    selector: Selector,
    external_ports: List[dict],
    master_files: dict,
    slave_names: dict,
    worker_io: Connection,
):
    """
    Adds external serial ports to the virtual network.

    This function integrates external serial ports into the virtual network by opening the ports
    and registering them with the selector and master files dictionary.

    Args:
        stack (ExitStack): Context manager for resource cleanup.
        selector (Selector): Selector instance for event monitoring.
        external_ports (List[dict]): List of dictionaries containing configuration details
            for external ports.
        master_files (dict): Dictionary mapping master file descriptors to their corresponding
            objects.
        slave_names (dict): Dictionary mapping slave names to their associated master file
            descriptors.
        worker_io (Connection): Worker I/O connection for communicating status updates.

    Raises:
        SerialConnectionConfigError: If an error occurs during port addition.
    """
    for con_params in external_ports:
        if con_params["port"] in slave_names:
            worker_io.send({"status": "EXIST", "data": con_params["port"]})
        else:
            try:
                port = Serial(**con_params)
                port_fd = port.fileno()
                os.set_blocking(port_fd, False)
                master_files[port_fd] = port
                slave_names[con_params["port"]] = port_fd
                stack.enter_context(master_files[port_fd])
                selector.register(port_fd, EVENT_READ)
                worker_io.send({"status": "OK", "data": con_params["port"]})
            # pylint: disable=broad-exception-caught
            except Exception as e:
                worker_io.send(
                    {
                        "status": "ERROR",
                        "data": {"error": str(e), "traceback": traceback.format_exc()},
                    }
                )


def remove_ports(
    selector: Selector,
    remove_list: List[str],
    master_files: dict,
    slave_names: dict,
    worker_io: Connection,
):
    """
    Remove ports from the network.

    This function removes specified ports from the virtual network by unregistering them from the
    selector and closing their associated resources.

    Args:
        selector (Selector): Selector instance for event monitoring.
        remove_list (List[str]): List of slave names to remove from the network.
        master_files (dict): Dictionary mapping master file descriptors to their corresponding
            objects.
        slave_names (dict): Dictionary mapping slave names to their associated master file
            descriptors.
        worker_io (Connection): Worker I/O connection for communicating status updates.

    Raises:
        SerialConnectionConfigError: If an error occurs during port removal.
    """
    for slave_name in remove_list:
        if slave_name in slave_names:
            try:
                master_fd = slave_names[slave_name]
                selector.unregister(master_fd)
                master_files[master_fd].close()
                del master_files[master_fd]
                del slave_names[slave_name]
                worker_io.send({"status": "OK", "data": slave_name})
            # pylint: disable=broad-exception-caught
            except Exception as e:
                worker_io.send(
                    {
                        "status": "ERROR",
                        "data": {"error": str(e), "traceback": traceback.format_exc()},
                    }
                )
        else:
            worker_io.send({"status": "NOT_EXIST", "data": slave_name})


def forward_data(selector: Selector, master_files: dict, loopback: bool = False):
    """
    Forward data to all ports of the network.

    This function forwards data received from one port to all other ports in the virtual network.
    If loopback is enabled, data is also sent back to the originating port.

    Args:
        selector (Selector): Selector instance for event monitoring.
        master_files (dict): Dictionary mapping master file descriptors to their corresponding
            objects.
        loopback (bool, optional): Whether to enable loopback mode. Defaults to False.

    Raises:
        SerialConnectionConfigError: If an error occurs during data forwarding.
    """
    for key, events in selector.select(timeout=1):
        key_fd = key.fileobj
        if events & EVENT_READ and isinstance(key_fd, int):
            try:
                data = master_files[key_fd].read()
                # Write to master files.
                # If loopback is False, don't write to the sending file.
                for fd, f in master_files.items():
                    if loopback or fd != key_fd:
                        f.write(data)
            except Exception:  # pylint: disable=broad-exception-caught
                pass


# pylint: disable=too-many-positional-arguments
def process_cmd(
    stack: ExitStack,
    selector: Selector,
    master_files: dict,
    slave_names: dict,
    worker_io: Connection,
    openpty_func: Optional[Callable] = None,
) -> bool:
    """
    Command processing function.

    This function processes incoming commands from the worker I/O connection. Supported commands
    include stopping the worker, removing ports, adding external ports, and generating virtual
    ports.

    Args:
        stack (ExitStack): Context manager for resource cleanup.
        selector (Selector): Selector instance for event monitoring.
        master_files (dict): Dictionary mapping master file descriptors to their corresponding
            objects.
        slave_names (dict): Dictionary mapping slave names to their associated master file
            descriptors.
        worker_io (Connection): Worker I/O connection for communicating status updates.
        openpty_func (Optional[Callable], optional): Function to open pseudo-terminal pairs.
            Defaults to pty.openpty.

    Returns:
        bool: True if the worker should continue running, False otherwise.

    Raises:
        SerialConnectionConfigError: If an error occurs during command processing.
    """
    if worker_io.poll():
        message = worker_io.recv()
        try:
            command = message["cmd"].lower()
        # pylint: disable=broad-exception-caught
        except Exception as e:
            worker_io.send(
                {
                    "status": "ERROR",
                    "data": {"error": str(e), "traceback": traceback.format_exc()},
                }
            )
            return True
        if command == "stop":
            return False
        if command == "remove":
            remove_list = message["data"]
            remove_ports(selector, remove_list, master_files, slave_names, worker_io)
        elif command == "add":
            external_ports = message["data"]
            add_external_ports(
                stack, selector, external_ports, master_files, slave_names, worker_io
            )
        elif command == "create":
            ports_number = message["data"]
            generate_virtual_ports(
                stack,
                selector,
                ports_number,
                master_files,
                slave_names,
                worker_io,
                openpty_func,
            )
    return True


def create_serial_network(
    worker_io: Connection,
    ports_number: int = 2,
    external_ports: Optional[List[dict]] = None,
    loopback: bool = False,
    openpty_func: Callable = pty.openpty,
) -> None:
    """
    Creates a network of virtual and existing serial ports.

    This function initializes a virtual network of serial ports, combining both virtual and external
    ports. Data received from one port is forwarded to all other ports in the network.

    Args:
        worker_io (Connection): Worker I/O connection for communicating status updates.
        ports_number (int, optional): Number of virtual ports to generate. Defaults to 2.
        external_ports (Optional[List[dict]], optional): List of external serial ports to integrate.
            Defaults to None.
        loopback (bool, optional): Enable loopback mode. Defaults to False.
        openpty_func (Callable, optional): Function to open pseudo-terminal pairs.
            Defaults to pty.openpty.

    Raises:
        SerialConnectionConfigError: If an error occurs during network creation.
    """
    # pylint: disable=too-many-locals
    master_files: dict[int, Union[BinaryIO, Serial]] = {}
    slave_names: dict[str, int] = {}
    keep_running: bool = True
    if external_ports is None:
        external_ports = []
    with Selector() as selector, ExitStack() as stack:
        generate_virtual_ports(
            stack,
            selector,
            ports_number,
            master_files,
            slave_names,
            worker_io,
            openpty_func,
        )
        add_external_ports(
            stack, selector, external_ports, master_files, slave_names, worker_io
        )
        while keep_running:
            keep_running = process_cmd(
                stack, selector, master_files, slave_names, worker_io, openpty_func
            )
            forward_data(selector, master_files, loopback)
