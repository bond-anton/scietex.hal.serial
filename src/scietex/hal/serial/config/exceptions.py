"""
Module defining exceptions related to serial connection configuration.

This module defines custom exceptions that are raised when invalid or inconsistent configuration
parameters are encountered while setting up serial connections.

Classes:
    - SerialConnectionConfigError: Raised when an invalid value is passed to the serial connection
      configuration.

Attributes:
    message (str): A descriptive error message explaining why the exception was raised.

Notes:
    - Subclasses `ValueError` to provide a more specific exception type for configuration issues.
    - Use this exception in situations where configuration validation fails due to incorrect input.
"""


class SerialConnectionConfigError(ValueError):
    """
    Custom exception indicating invalid or unsupported values in serial connection configuration.

    Attributes:
        message (str): Error message describing the issue.

    Raises:
        ValueError: When an invalid configuration parameter is detected.
    """
