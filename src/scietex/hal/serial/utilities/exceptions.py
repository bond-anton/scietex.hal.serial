"""
Module defining exceptions related to Modbus operations.

This module defines custom exceptions that are raised when a Modbus read, write, or execute
operation fails at runtime. Strict error handling is the default; pass ``raise_on_error=False``
to opt out and return `None` on failure instead.

Classes:
    - ModbusOperationError: Raised when a Modbus read, write, or execute operation fails.

Notes:
    - Subclasses `Exception` to represent a runtime protocol/transport failure rather than a
      configuration error.
    - The read/write wrappers and `RS485Client` methods raise this exception on failure by default
      (`raise_on_error=True`). Passing `raise_on_error=False` restores the legacy behavior of
      returning `None` on failure.
"""


class ModbusOperationError(Exception):
    """
    Custom exception indicating a failed Modbus operation.

    Attributes:
        message (str): Error message describing the issue.
    """
