"""
Virtual serial port pair creation.

This module extends the functionality of the `VirtualSerialNetwork` class to specifically handle
the creation of a pair of virtual serial ports. This is useful for simulating bidirectional
communication between two endpoints over a virtual serial link.

Classes:
    - VirtualSerialPair: Specialized subclass of `VirtualSerialNetwork` designed to manage a pair
      of virtual serial ports.

Example:
    >>> vsp = VirtualSerialPair()
    >>> vsp.start()

The `VirtualSerialPair` class simplifies the setup of a virtual serial environment, making it
easier to simulate and test serial communication without requiring physical hardware.
"""

from typing import Optional, Callable, List
from logging import Logger

from .virtual_serial_network import VirtualSerialNetwork
from ..config import SerialConnectionMinimalConfig


class VirtualSerialPair(VirtualSerialNetwork):
    """
    A virtual serial port pair for simulating serial communication.

    This class inherits from `VirtualSerialNetwork` but is specialized to manage exactly two
    virtual serial ports, representing a bi-directional communication channel. This makes it
    suitable for testing applications that rely on serial communication.

    Attributes:
        serial_ports (List[str]): List of active virtual serial ports. Should always contain
            exactly two ports when the network is initialized correctly.

    Methods:
        start(self, openpty_func=None): Initializes the virtual serial pair. If fewer than two
            ports are successfully created, the network is stopped automatically.
        add(self, external_ports: List[SerialConnectionMinimalConfig]): Disabled for this class
            since adding external ports does not apply to a fixed-pair configuration.
        create(self, ports_num: int): Disabled for this class since additional virtual ports beyond
            the initial pair are not allowed.
        remove(self, remove_list: List[str]): Disabled for this class because removing ports would
            disrupt the pre-configured pair.

    Example:
        >>> vsp = VirtualSerialPair()
        >>> vsp.start()
    """

    def __init__(self, logger: Optional[Logger] = None) -> None:
        """
        Initialize the VirtualSerialPair instance.

        Args:
            logger (Optional[Logger], optional): A logging handler for recording operational
                information. Defaults to a basic logger if none is provided.
        """
        super().__init__(
            virtual_ports_num=2, external_ports=None, loopback=False, logger=logger
        )

    def start(self, openpty_func: Optional[Callable] = None):
        """
        Start the virtual serial pair.

        This method initializes the virtual serial network, ensuring that exactly two virtual ports
        are created. If the initialization fails to produce two ports, the network is stopped
        immediately.

        Args:
            openpty_func (Optional[Callable], optional): An alternative function for opening
                pseudo-terminal pairs. Defaults to `pty.openpty`.

        Raises:
            RuntimeError: If the network fails to create the required two ports.
        """
        super().start(openpty_func)
        if self.virtual_ports_num < 2:
            self.logger.error("VSP: Failed to create virtual serial ports.")
            self.stop()

    def add(self, external_ports: List[SerialConnectionMinimalConfig]):
        """
        Add external ports (disabled).

        Since `VirtualSerialPair` is designed to work exclusively with its own pair of virtual
        ports, adding external ports is not applicable and will result in a log message.

        Args:
            external_ports (List[SerialConnectionMinimalConfig]): Ignored in this context.
        """
        self.logger.info(
            "VSP: Adding external ports is not supported for Virtual Serial Pairs."
        )

    def create(self, ports_num: int):
        """
        Create additional virtual ports (disabled).

        Creating additional virtual ports beyond the initial pair is not supported in
        `VirtualSerialPair` and will result in a log message.

        Args:
            ports_num (int): Ignored in this context.
        """
        self.logger.info("VSP: Creating additional virtual ports is not supported.")

    def remove(self, remove_list: List[str]):
        """
        Remove ports (disabled).

        Removing ports from the pair would disrupt the pre-configured setup, so this action
        is disabled and results in a log message.

        Args:
            remove_list (List[str]): Ignored in this context.
        """
        self.logger.info(
            "VSP: Removing ports is not supported for Virtual Serial Pairs."
        )
