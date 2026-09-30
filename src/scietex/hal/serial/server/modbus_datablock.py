"""
Custom DataBlock for the Modbus server.

This module defines a sequential payload block for use in a Modbus server.

Dependencies:
    - pymodbus: Provides base classes and utilities for building Modbus servers and clients.

Classes:
    - ReactiveSequentialDataBlock: A `ModbusSequentialDataBlock` subclass kept for API
      compatibility. pymodbus >= 3.15 reduced the base class to a deprecated shim and
      removed the `setValues` hook, so the former `on_change` callback is no longer
      supported; the class now only carries the initial register values.
"""

from pymodbus.datastore import ModbusSequentialDataBlock


class ReactiveSequentialDataBlock(ModbusSequentialDataBlock):
    """
    Sequential data block for the Modbus server.

    Retained as a named subclass of `ModbusSequentialDataBlock` for backwards
    compatibility. The reactive `on_change` callback was removed because pymodbus
    >= 3.15 no longer exposes a `setValues` hook on the base class; register writes
    are handled internally by the simulator and cannot be intercepted here.
    """
