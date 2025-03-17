"""
Virtual serial port network creation.

This module provides a high-level abstraction for managing a virtual network of serial ports.
It allows the creation, addition, and removal of virtual and external serial ports, enabling
seamless interaction between simulated and real-world devices.

Classes:
    - VirtualSerialNetwork: Manages the lifecycle of a virtual serial port network, including
      starting, stopping, adding, creating, and removing ports.

Functions:
    - _ext_ports_remove_duplicates(self): Removes duplicate entries from the list of external
      ports.
    - _update_ext_ports(self, ports_connected: List[str]): Updates the list of external ports after
      successful connection attempts.

Attributes:
    - virtual_ports_num (int): The number of virtual ports currently active in the network.
    - external_ports (List[SerialConnectionMinimalConfig]): List of external serial ports
      configured for integration into the virtual network.
    - serial_ports (List[str]): Combined list of all active ports (both virtual and external) in
      the network.
    - loopback (bool): Flag indicating whether loopback mode is enabled. In this mode, data sent
      from a port is also received by itself.
    - logger (logging.Logger): Logging handler for recording debug, info, warning, and error
      messages.

This class encapsulates the complexity of managing multiple serial ports, allowing users to focus
on higher-level tasks such as simulating device behavior or integrating external hardware.
"""

from typing import Union, List, Optional, Callable
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from logging import Logger, getLogger

from .worker import create_serial_network
from ..config import SerialConnectionMinimalConfig


# pylint: disable=too-many-instance-attributes
class VirtualSerialNetwork:
    """
    A virtual serial port network management.

    This class serves as a high-level API for creating, managing, and interacting with a virtual
    network of serial ports. It handles the initialization, addition, and removal of both virtual
    and external serial ports, providing a unified interface for controlling these operations.

    Attributes:
        virtual_ports_num (int): The number of virtual ports initially requested when the network
            starts.
        external_ports (List[SerialConnectionMinimalConfig]): A list of external serial ports that
            can be integrated into the virtual network.
        serial_ports (List[str]): A combined list of all active ports (both virtual and external)
            in the network.
        loopback (bool): Determines whether loopback mode is enabled. In loopback mode, data sent
            from a port is also received by itself.
        logger (Logger): A logging handler for recording debug, info, warning, and error messages
            related to the virtual network's operation.

    Methods:
        start(self, openpty_func=None): Starts the virtual serial network and initializes
            communication.
        stop(self): Stops the virtual serial network and cleans up resources.
        add(self, external_ports: List[SerialConnectionMinimalConfig]): Adds external serial ports
            to the network.
        create(self, ports_num: int): Creates additional virtual ports in the network.
        remove(self, remove_list: List[str]): Removes specified ports from the network.
    """

    def __init__(
        self,
        virtual_ports_num: int = 2,
        external_ports: Optional[List[SerialConnectionMinimalConfig]] = None,
        loopback: bool = False,
        logger: Optional[Logger] = None,
    ) -> None:
        """
        Initializes the VirtualSerialNetwork instance.

        Args:
            virtual_ports_num (int, optional): The initial number of virtual ports to create.
                Defaults to 2.
            external_ports (Optional[List[SerialConnectionMinimalConfig]], optional): A list
                of external serial ports to integrate into the virtual network. Defaults to None.
            loopback (bool, optional): Enables loopback mode where data sent from a port is also
                received by itself. Defaults to False.
            logger (Optional[Logger], optional): A logging handler for recording operational
                information. Defaults to a basic logger if none is provided.
        """
        self.__master_io: Optional[Connection] = None
        self.__worker_io: Optional[Connection] = None
        self.__p: Union[Process, None] = None
        self.loopback: bool = loopback
        self.external_ports: List[SerialConnectionMinimalConfig] = (
            external_ports if external_ports is not None else []
        )
        self._ext_ports_remove_duplicates()
        self.virtual_ports_num: int = virtual_ports_num
        self.serial_ports: List[str] = []

        self.logger: Logger = logger if isinstance(logger, Logger) else getLogger()

    def start(self, openpty_func: Optional[Callable] = None):
        """
        Start the virtual serial network and initialize communication.

        This method initiates the virtual network by spawning a separate process (`worker`)
        responsible for managing the ports. Once started, the network begins listening for commands
        and data.

        Args:
            openpty_func (Optional[Callable], optional): An alternative function for opening
                pseudo-terminal pairs. Defaults to `pty.openpty`.

        Raises:
            RuntimeError: If the network is already running.
        """
        self.logger.debug("VSN: STARTING")
        self.__master_io, self.__worker_io = Pipe()
        external_ports = None
        if self.external_ports:
            external_ports = [
                con_params.to_dict() for con_params in self.external_ports
            ]
        virtual_ports_num = self.virtual_ports_num
        self.__p = Process(
            target=create_serial_network,
            args=(
                self.__worker_io,
                virtual_ports_num,
                external_ports,
                self.loopback,
                openpty_func,
            ),
        )
        self.__p.start()
        self.virtual_ports_num = 0
        for _ in range(virtual_ports_num):
            response = self.__master_io.recv()
            if response["status"] == "ERROR":
                self.logger.error("VSN: ERROR (%s)", response["data"]["error"])
            elif response["status"] == "OK":
                self.serial_ports.append(response["data"])
                self.virtual_ports_num += 1
        ports_connected = []
        for _ in range(len(self.external_ports)):
            response = self.__master_io.recv()
            if response["status"] == "ERROR":
                self.logger.error("VSN: ERROR (%s)", response["data"]["error"])
            elif response["status"] == "OK":
                ports_connected.append(response["data"])
        self._update_ext_ports(ports_connected)
        self._ext_ports_remove_duplicates()
        self.serial_ports += ports_connected
        self.serial_ports = list(set(self.serial_ports))
        self.logger.info("VSN: STARTED")
        self.logger.info("VSN: %s", self.serial_ports)

    def _ext_ports_remove_duplicates(self):
        """
        Removes duplicate entries from the list of external ports.

        Duplicate ports are identified by comparing their `port` attributes.
        """
        new_external_ports_list = []
        for port_params in self.external_ports:
            duplicate = False
            for added_port in new_external_ports_list:
                if port_params.port == added_port.port:
                    duplicate = True
                    break
            if not duplicate:
                new_external_ports_list.append(port_params)
        self.external_ports = new_external_ports_list

    def _update_ext_ports(self, ports_connected: List[str]):
        """
        Updates the list of external ports after successful connection attempts.

        Only those external ports that were successfully connected remain in the updated list.

        Args:
            ports_connected (List[str]): List of successfully connected external ports.
        """
        new_external_ports_list = []
        for port_params in self.external_ports:
            for port_name in ports_connected:
                if port_params.port == port_name:
                    new_external_ports_list.append(port_params)
                    break
        self.external_ports = new_external_ports_list

    def stop(self):
        """
        Stop the virtual serial network.

        Sends a stop signal to the worker process, waits for termination, and cleans up all
            resources.
        """
        if self.__p is not None:
            self.logger.debug("VSN: STOPPING")
            self.__master_io.send({"cmd": "stop"})
            self.__p.join(timeout=5)  # Wait for the process to terminate

            self.__p = None
            self.__master_io, self.__worker_io = None, None
            self.serial_ports = []
            self.logger.info("VSN: STOPPED")

    def add(self, external_ports: List[SerialConnectionMinimalConfig]):
        """
        Add external ports to the network.

        Attempts to connect each provided external port to the virtual network.
        Successfully connected ports are appended to the internal lists.

        Args:
            external_ports (List[SerialConnectionMinimalConfig]): List of external serial ports
                to add.
        """
        if self.__master_io is not None:
            ext_ports = [
                con_params.to_dict() for con_params in list(set(external_ports))
            ]
            self.__master_io.send({"cmd": "add", "data": ext_ports})
            ports_connected = []
            for _ in range(len(ext_ports)):
                response = self.__master_io.recv()
                if response["status"] == "ERROR":
                    self.logger.error("VSN: ERROR (%s)", response["data"]["error"])
                elif response["status"] == "EXIST":
                    self.logger.error("VSN: Port (%s) already added.", response["data"])
                elif response["status"] == "OK":
                    for port in list(set(external_ports)):
                        if port.port == response["data"]:
                            ports_connected.append(port)
                            break
            self.external_ports += ports_connected
            self._ext_ports_remove_duplicates()
            self.serial_ports += [port.port for port in ports_connected]
            self.serial_ports = list(set(self.serial_ports))

    def create(self, ports_num: int):
        """
        Create new virtual ports in the network.

        Requests the creation of additional virtual ports, increasing the total number of available
        virtual ports in the network.

        Args:
            ports_num (int): Number of new virtual ports to create.
        """
        if self.__master_io is not None:
            self.__master_io.send({"cmd": "create", "data": ports_num})
            for _ in range(ports_num):
                response = self.__master_io.recv()
                if response["status"] == "ERROR":
                    self.logger.error("VSN: ERROR (%s)", response["data"]["error"])
                elif response["status"] == "OK":
                    self.serial_ports.append(response["data"])
                    self.virtual_ports_num += 1

    def remove(self, remove_list: List[str]):
        """
        Remove port from the network.

        Unregisters and closes the specified ports, effectively removing them
        from the virtual network.

        Args:
            remove_list (List[str]): List of ports to remove from the network.
        """
        if self.__master_io is not None:
            self.__master_io.send({"cmd": "remove", "data": remove_list})
            removed_ports = []
            for _ in range(len(remove_list)):
                response = self.__master_io.recv()
                if response["status"] == "ERROR":
                    self.logger.error("VSN: ERROR (%s)", response["data"]["error"])
                if response["status"] == "NOT_EXIST":
                    self.logger.warning("VSN: Port %s not found", response["data"])
                elif response["status"] == "OK":
                    removed_ports.append(response["data"])
            for port in removed_ports:
                found = False
                for i, ext_port in enumerate(self.external_ports):
                    if ext_port.port == port:
                        del self.external_ports[i]
                        found = True
                        break
                if not found:
                    self.virtual_ports_num -= 1
            self.serial_ports = list(set(self.serial_ports) - set(removed_ports))
