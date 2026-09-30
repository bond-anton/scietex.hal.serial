"""
Module defining exceptions related to the virtual serial network.

This module defines custom exceptions that are raised when the virtual serial network
worker process fails or enters an unexpected state at runtime.

Classes:
    - VirtualSerialNetworkError: Raised when the virtual serial network worker process
      is not alive and can no longer process commands.

Notes:
    - Subclasses `Exception` to represent a runtime/process failure rather than a
      configuration error.
    - Use this exception when the worker process dies and subsequent commands cannot
      be processed.
"""


class VirtualSerialNetworkError(Exception):
    """
    Custom exception indicating a runtime failure of the virtual serial network worker.

    Attributes:
        message (str): Error message describing the issue.
    """
