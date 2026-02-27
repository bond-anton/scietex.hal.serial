"""
Worker function for serial network creation and management.

This module handles the generation, addition, removal, and payload forwarding for virtual and
physical serial ports. It provides functions to manage a virtual network of serial devices,
ensuring proper handling of incoming commands and payload exchange between connected ports.

Functions:
    - generate_virtual_ports(stack, selector, ports_number, master_files, slave_names,
        worker_io, openpty_func=None):
        Generates a specified number of virtual serial ports using the provided openpty function.
    - add_external_ports(stack, selector, external_ports, master_files, slave_names, worker_io):
        Adds external serial ports to the virtual network.
    - remove_ports(selector, remove_list, master_files, slave_names, worker_io):
        Removes specified ports from the virtual network.
    - forward_data(selector, master_files, loopback=False):
        Forwards payload between connected ports in the virtual network.
    - process_cmd(stack, selector, master_files, slave_names, worker_io, openpty_func=None):
        Processes incoming commands from the worker I/O connection.
    - create_serial_network(worker_io, ports_number=2, external_ports=None,
        loopback=False, openpty_func=pty.openpty):
        Creates a virtual network of serial ports and manages payload flow between them.

Raises:
    Various exceptions may occur during port operations, such as IOErrors or configuration errors.
    The exceptions are caught and handled gracefully, ensuring the stability of the virtual network.

This module enables developers to simulate and test complex serial device interactions without
relying on physical hardware, making it ideal for testing and debugging scenarios.
"""

from typing import Optional, Callable, BinaryIO
import os
import logging
from logging import Logger, getLogger
from logging.handlers import RotatingFileHandler
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
    master_cache: dict,
    slave_names: dict,
    worker_io: Connection,
    openpty_func: Optional[Callable] = None,
    logger: Logger | None = None,
):
    """
    Generate `ports_number` virtual ports using openpty_func.

    This function creates the specified number of virtual serial ports using the provided openpty
    function. Each created port is registered with the selector and added to the master files and
    device_id names dictionaries.

    Args:
        stack (ExitStack): Context manager for resource cleanup.
        selector (Selector): Selector instance for event monitoring.
        ports_number (int): Number of virtual ports to generate.
        master_files (dict): Dictionary mapping master file descriptors to their corresponding
            objects.
        master_cache (dict): Dictionary mapping master file descriptors to their cached data.
        slave_names (dict): Dictionary mapping device_id names to their associated master file
            descriptors.
        worker_io (Connection): Worker I/O connection for communicating status updates.
        openpty_func (Optional[Callable], optional): Function to open pseudo-terminal pairs.
            Defaults to pty.openpty.
        logger (Logger, optional): A logging handler for recording debug, info, warning, and error
            messages related to virtual port generation. Defaults to a basic logger if none
            is provided.

    Raises:
        SerialConnectionConfigError: If an error occurs during port creation.
    """
    _logger: Logger = logger if isinstance(logger, Logger) else getLogger()
    openpty_func = openpty_func if callable(openpty_func) else pty.openpty
    for _ in range(ports_number):
        try:
            master_fd, slave_fd = openpty_func()
            tty.setraw(master_fd)
            os.set_blocking(master_fd, False)
            slave_name = os.ttyname(slave_fd)
            # pylint: disable=consider-using-with
            master_files[master_fd] = open(master_fd, "r+b", buffering=0)
            master_cache[master_fd] = b""
            slave_names[slave_name] = master_fd
            stack.enter_context(master_files[master_fd])
            selector.register(master_fd, EVENT_READ)
            _logger.debug(
                "VSN: Worker: Successfully generated virtual port '%s'", slave_name
            )
            worker_io.send({"status": "OK", "payload": slave_name})
        # pylint: disable=broad-exception-caught
        except Exception as e:
            _logger.debug("VSN: Worker: Failed to generate virtual port: %s", e)
            worker_io.send(
                {
                    "status": "ERROR",
                    "payload": {"error": str(e), "traceback": traceback.format_exc()},
                }
            )


# pylint: disable=too-many-positional-arguments
def add_external_ports(
    stack: ExitStack,
    selector: Selector,
    external_ports: list[dict],
    master_files: dict,
    master_cache: dict,
    slave_names: dict,
    worker_io: Connection,
    logger: Logger | None = None,
):
    """
    Adds external serial ports to the virtual network.

    This function integrates external serial ports into the virtual network by opening the ports
    and registering them with the selector and master files dictionary.

    Args:
        stack (ExitStack): Context manager for resource cleanup.
        selector (Selector): Selector instance for event monitoring.
        external_ports (list[dict]): List of dictionaries containing configuration details
            for external ports.
        master_files (dict): Dictionary mapping master file descriptors to their corresponding
            objects.
        master_cache (dict): Dictionary mapping master file descriptors to their cached data.
        slave_names (dict): Dictionary mapping device_id names to their associated master file
            descriptors.
        worker_io (Connection): Worker I/O connection for communicating status updates.
        logger (Logger, optional): A logging handler for recording debug, info, warning, and error
            messages related to external port addition. Defaults to a basic logger if none
            is provided.

    Raises:
        SerialConnectionConfigError: If an error occurs during port addition.
    """
    _logger: Logger = logger if isinstance(logger, Logger) else getLogger()
    for con_params in external_ports:
        _logger.debug(
            "VSN: Worker: Attempting to add external port '%s'", con_params["port"]
        )
        if con_params["port"] in slave_names:
            _logger.debug(
                "VSN: Worker: External port '%s' already exists", con_params["port"]
            )
            worker_io.send({"status": "EXIST", "payload": con_params["port"]})
        else:
            try:
                port = Serial(**con_params)
                port_fd = port.fileno()
                os.set_blocking(port_fd, False)
                master_files[port_fd] = port
                master_cache[port_fd] = b""
                slave_names[con_params["port"]] = port_fd
                stack.enter_context(master_files[port_fd])
                selector.register(port_fd, EVENT_READ)
                _logger.debug(
                    "VSN: Worker: Successfully added external port '%s'",
                    con_params["port"],
                )
                worker_io.send({"status": "OK", "payload": con_params["port"]})
            # pylint: disable=broad-exception-caught
            except Exception as e:
                _logger.warning(
                    "VSN: Worker: Failed to add external port '%s': %s",
                    con_params["port"],
                    e,
                )
                worker_io.send(
                    {
                        "status": "ERROR",
                        "payload": {
                            "error": str(e),
                            "traceback": traceback.format_exc(),
                        },
                    }
                )


def remove_ports(
    selector: Selector,
    remove_list: list[str],
    master_files: dict,
    master_cache: dict,
    slave_names: dict,
    worker_io: Connection,
    logger: Logger | None = None,
):
    """
    Remove ports from the network.

    This function removes specified ports from the virtual network by unregistering them from the
    selector and closing their associated resources.

    Args:
        selector (Selector): Selector instance for event monitoring.
        remove_list (list[str]): List of device_id names to remove from the network.
        master_files (dict): Dictionary mapping master file descriptors to their corresponding
            objects.
        master_cache (dict): Dictionary mapping master file descriptors to their cached data.
        slave_names (dict): Dictionary mapping device_id names to their associated master file
            descriptors.
        worker_io (Connection): Worker I/O connection for communicating status updates.
        logger (Logger, optional): A logging handler for recording debug, info, warning, and error
            messages related to port removal. Defaults to a basic logger if none is provided.

    Raises:
        SerialConnectionConfigError: If an error occurs during port removal.
    """
    _logger: Logger = logger if isinstance(logger, Logger) else getLogger()
    for slave_name in remove_list:
        _logger.debug("VSN: Worker: Attempting to remove slave name '%s'", slave_name)
        if slave_name in slave_names:
            try:
                master_fd = slave_names[slave_name]
                selector.unregister(master_fd)
                master_files[master_fd].close()
                master_cache.pop(master_fd, None)
                del master_files[master_fd]
                del slave_names[slave_name]
                _logger.debug(
                    "VSN: Worker: Successfully removed slave name '%s'", slave_name
                )
                worker_io.send({"status": "OK", "payload": slave_name})
            # pylint: disable=broad-exception-caught
            except Exception as e:
                _logger.warning(
                    "VSN: Worker: Failed to remove slave name '%s': %s", slave_name, e
                )
                worker_io.send(
                    {
                        "status": "ERROR",
                        "payload": {
                            "error": str(e),
                            "traceback": traceback.format_exc(),
                        },
                    }
                )
        else:
            _logger.debug("VSN: Worker: Slave name '%s' does not exist", slave_name)
            worker_io.send({"status": "NOT_EXIST", "payload": slave_name})


def setup_data_logging(
    app_name="VSN",
    log_file="vsn-data.log",
    max_bytes=10 * 1024 * 1024,
    backup_count=5,
    level=logging.DEBUG,
) -> Logger:
    """Sets up a logger for data payload logging with rotation."""
    logger = logging.getLogger(app_name)
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s:%(funcName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.handlers.clear()
    logger.addHandler(file_handler)

    return logger


# pylint: disable=too-many-locals, too-many-branches
def forward_data(
    selector: Selector,
    master_files: dict,
    master_cache: dict,
    slave_names: dict,
    loopback: bool = False,
    logger: Logger | None = None,
    data_logging_file: str | None = None,
    data_logging_splitter: bytes | None = None,
):
    """
    Forward payload to all ports of the network.

    This function forwards payload received from one port to all other ports in the virtual network.
    If loopback is enabled, payload is also sent back to the originating port.

    Args:
        selector (Selector): Selector instance for event monitoring.
        master_files (dict): Dictionary mapping master file descriptors to their corresponding
            objects.
        master_cache (dict): Dictionary mapping master file descriptors to their cached data.
        slave_names (dict): Dictionary mapping device_id names to their associated master file
            descriptors.
        loopback (bool, optional): Whether to enable loopback mode. Defaults to False.
        logger (Logger, optional): A logging handler for recording debug, info, warning, and error
            messages related to payload forwarding. Defaults to a basic logger if none is provided.
        data_logging_file (str, optional): Path to a file for logging raw data payloads. If None,
            data logging is disabled. Defaults to None.
        data_logging_splitter (bytes, optional): Optional byte sequence to split logged data into
            separate log entries. If None, data is logged as a single entry. Defaults to None.

    Raises:
        SerialConnectionConfigError: If an error occurs during payload forwarding.
    """
    _logger: Logger = logger if isinstance(logger, Logger) else getLogger()
    data_logger = None
    if data_logging_file and isinstance(data_logging_file, str):
        data_logger = setup_data_logging(
            app_name="VSNDataLogger",
            log_file=data_logging_file,
            max_bytes=10 * 1024 * 1024,
            backup_count=5,
            level=logging.DEBUG,
        )
    # pylint: disable=too-many-nested-blocks
    for key, events in selector.select(timeout=1):
        key_fd = key.fileobj
        if events & EVENT_READ and isinstance(key_fd, int):
            try:
                data = master_files[key_fd].read()
                _logger.debug("VSN: Worker: Received data from fd %s: %s", key_fd, data)
                if data_logger and isinstance(data_logger, Logger):
                    master_cache[key_fd] += data
                    key_fd_name = None
                    for name, fd in slave_names.items():
                        if fd == key_fd:
                            key_fd_name = name
                            break
                    if data_logging_splitter:
                        log_data = master_cache[key_fd].split(data_logging_splitter)
                        if len(log_data) > 1:
                            for i in range(len(log_data) - 1):
                                log_data_hex_string = log_data[i].hex(" ").upper()
                                data_logger.info(
                                    "%s | %s | %s",
                                    key_fd_name,
                                    log_data_hex_string,
                                    log_data[i],
                                )
                            master_cache[key_fd] = log_data[-1]
                    else:
                        log_data = [master_cache[key_fd]]
                        log_data_hex_string = log_data[0].hex(" ").upper()
                        master_cache[key_fd] = b""
                        data_logger.info(
                            "%s | %s | %s",
                            key_fd_name,
                            log_data_hex_string,
                            log_data[0],
                        )
                # Write to master files.
                # If loopback is False, don't write to the sending file.
                for fd, f in master_files.items():
                    if loopback or fd != key_fd:
                        f.write(data)
            except Exception:  # pylint: disable=broad-exception-caught
                _logger.debug("VSN: Worker: Failed to forward data from fd %s", key_fd)


# pylint: disable=too-many-positional-arguments
def process_cmd(
    stack: ExitStack,
    selector: Selector,
    master_files: dict,
    master_cache: dict,
    slave_names: dict,
    worker_io: Connection,
    openpty_func: Optional[Callable] = None,
    logger: Logger | None = None,
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
        master_cache (dict): Dictionary mapping master file descriptors to their cached data.
        slave_names (dict): Dictionary mapping device_id names to their associated master file
            descriptors.
        worker_io (Connection): Worker I/O connection for communicating status updates.
        openpty_func (Optional[Callable], optional): Function to open pseudo-terminal pairs.
            Defaults to pty.openpty.
        logger (Logger): A logging handler for recording debug, info, warning, and error messages
            related to the virtual network's operation. Defaults to a basic logger if none
            is provided.

    Returns:
        bool: True if the worker should continue running, False otherwise.

    Raises:
        SerialConnectionConfigError: If an error occurs during command processing.
    """
    if worker_io.poll():
        _logger: Logger = logger if isinstance(logger, Logger) else getLogger()
        message = worker_io.recv()
        try:
            command = message["cmd"].lower()
        # pylint: disable=broad-exception-caught
        except Exception as e:
            worker_io.send(
                {
                    "status": "ERROR",
                    "payload": {"error": str(e), "traceback": traceback.format_exc()},
                }
            )
            return True
        if command == "stop":
            return False
        if command == "remove":
            remove_list = message["payload"]
            remove_ports(
                selector,
                remove_list,
                master_files,
                master_cache,
                slave_names,
                worker_io,
                _logger,
            )
        elif command == "add":
            external_ports = message["payload"]
            add_external_ports(
                stack,
                selector,
                external_ports,
                master_files,
                master_cache,
                slave_names,
                worker_io,
                _logger,
            )
        elif command == "create":
            ports_number = message["payload"]
            generate_virtual_ports(
                stack,
                selector,
                ports_number,
                master_files,
                master_cache,
                slave_names,
                worker_io,
                openpty_func,
                _logger,
            )
    return True


def create_serial_network(
    worker_io: Connection,
    ports_number: int = 2,
    external_ports: Optional[list[dict]] = None,
    loopback: bool = False,
    openpty_func: Callable = pty.openpty,
    logger: Logger | None = None,
    data_logging_file: str | None = None,
    data_logging_splitter: bytes | None = None,
) -> None:
    """
    Creates a network of virtual and existing serial ports.

    This function initializes a virtual network of serial ports, combining both virtual and external
    ports. Data received from one port is forwarded to all other ports in the network.

    Args:
        worker_io (Connection): Worker I/O connection for communicating status updates.
        ports_number (int, optional): Number of virtual ports to generate. Defaults to 2.
        external_ports (Optional[list[dict]], optional): List of external serial ports to integrate.
            Defaults to None.
        loopback (bool, optional): Enable loopback mode. Defaults to False.
        openpty_func (Callable, optional): Function to open pseudo-terminal pairs.
            Defaults to pty.openpty.
        logger (Logger): A logging handler for recording debug, info, warning, and error messages
            related to the virtual network's operation. Defaults to a basic logger if none
            is provided.
        data_logging_file (str, optional): Path to a file for logging raw data payloads. If None,
            data logging is disabled. Defaults to None.
        data_logging_splitter (bytes, optional): Optional byte sequence to split logged data into
            separate log entries. If None, data is logged as a single entry. Defaults to None.

    Raises:
        SerialConnectionConfigError: If an error occurs during network creation.
    """
    # pylint: disable=too-many-locals
    _logger: Logger = logger if isinstance(logger, Logger) else getLogger()
    master_files: dict[int, BinaryIO | Serial] = {}
    master_cache: dict[int, bytes] = {}
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
            master_cache,
            slave_names,
            worker_io,
            openpty_func,
            _logger,
        )
        add_external_ports(
            stack,
            selector,
            external_ports,
            master_files,
            master_cache,
            slave_names,
            worker_io,
            _logger,
        )
        while keep_running:
            keep_running = process_cmd(
                stack,
                selector,
                master_files,
                master_cache,
                slave_names,
                worker_io,
                openpty_func,
                _logger,
            )
            forward_data(
                selector,
                master_files,
                master_cache,
                slave_names,
                loopback,
                logger=_logger,
                data_logging_file=data_logging_file,
                data_logging_splitter=data_logging_splitter,
            )
