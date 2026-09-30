"""
Module defining exceptions related to Modbus operations.

This module defines custom exceptions that are raised when a Modbus read, write, or execute
operation fails at runtime and the caller has opted into strict error handling via the
``raise_on_error`` parameter.

Classes:
    - ModbusOperationError: Raised when a Modbus read, write, or execute operation fails.

Notes:
    - Subclasses `Exception` to represent a runtime protocol/transport failure rather than a
      configuration error.
    - By default the read/write wrappers and `RS485Client` methods return `None` on failure; this
      exception is raised only when `raise_on_error=True`.
"""


class ModbusOperationError(Exception):
    """
    Custom exception indicating a failed Modbus operation.

    Attributes:
        message (str): Error message describing the issue.
    """
