"""
Module defining exceptions for the Modbus gateway.

This module defines custom exceptions raised by the gateway: configuration
errors (invalid or unresolvable gateway config) and runtime errors (bus or
translation failures).

Classes:
    - GatewayConfigError: Raised when gateway configuration is invalid.
    - GatewayError: Raised when a gateway runtime operation fails.

Notes:
    - `GatewayConfigError` subclasses `ValueError`, matching the existing
      `SerialConnectionConfigError` convention for configuration problems.
    - `GatewayError` subclasses `Exception`, matching `ModbusOperationError`
      for runtime protocol/transport failures.
"""


class GatewayConfigError(ValueError):
    """
    Custom exception indicating invalid or unsupported gateway configuration.

    Attributes:
        message (str): Error message describing the issue.
    """


class GatewayError(Exception):
    """
    Custom exception indicating a failed gateway runtime operation.

    Attributes:
        message (str): Error message describing the issue.
    """
