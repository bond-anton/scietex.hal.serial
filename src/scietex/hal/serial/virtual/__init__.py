"""
Virtual serial network organization module.

This module consolidates and exports the core components of the virtual serial network system,
providing easy access to classes like `VirtualSerialNetwork` and `VirtualSerialPair`.
Developers can use these classes to simulate and manage virtual serial ports for testing purposes.

Exported Classes:
    - VirtualSerialNetwork: Base class for managing a full-fledged virtual serial network,
      supporting both virtual and external ports.
    - VirtualSerialPair: Specialized subclass for managing a pair of virtual serial ports,
      useful for simulating bidirectional communication between two endpoints.

Usage:
    To create and manage a virtual serial network:
    ```python
    from virtual import VirtualSerialNetwork

    vsn = VirtualSerialNetwork(virtual_ports_num=2)
    vsn.start()
    ```

    To create a pair of virtual serial ports:
    ```python
    from virtual import VirtualSerialPair

    vsp = VirtualSerialPair()
    vsp.start()
    ```

This module streamlines the workflow for developers who need to simulate serial communication
without physical hardware, offering a versatile toolset for testing and prototyping.
"""

from .virtual_serial_network import VirtualSerialNetwork
from .virtual_serial_pair import VirtualSerialPair
