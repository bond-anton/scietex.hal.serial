"""
Mock functions collection.

This module provides mock functions for testing purposes. Mocks allow replacing real function calls
with controlled behaviors, helping to isolate specific parts of code under test.
This is particularly useful when working with external dependencies or resources that might be
unavailable during testing.

Functions:
    - mock_openpty(): Simulates failure of `os.openpty()` by raising an OSError.

Mocks are indispensable tools for writing reliable unit tests, especially when dealing with complex
or unpredictable dependencies.
"""


def mock_openpty():
    """
    Mock os.openpty to raise an OSError.

    This function replaces the original `os.openpty()` function during testing to simulate
    situations where pseudo-terminal creation fails. It raises an OSError to trigger
    error-handling paths in your application.

    Raises:
        OSError: Always raised to mimic a failed terminal creation scenario.

    Use cases:
        - Testing error recovery logic when opening terminals fails.
        - Emulating conditions where system resources are exhausted.
    """
    raise OSError("Failed to create pseudo-terminal")
