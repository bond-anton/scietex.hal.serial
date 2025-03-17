"""
Serial communication helper functions.

This module contains utility functions for calculating common checksums used in serial
communication protocols. Specifically, it provides methods for computing CRC-16/Modbus
checksums and Longitudinal Redundancy Check (LRC).

Functions:
    - check_sum(payload: bytes) -> int:
        Computes the CRC-16/Modbus checksum for the given payload data.
    - lrc(payload: bytes) -> int:
        Calculates the Longitudinal Redundancy Check (LRC) for the given payload data.
    - check_lrc(message: bytes) -> bool:
        Verifies the correctness of the LRC byte at the end of the message.

Checksum algorithms play a critical role in ensuring data integrity during serial communications.
CRC-16/Modbus is widely used in industrial protocols like Modbus RTU, while LRC is simpler
but still effective.

This module ensures that checksum calculations adhere to established standards, improving
reliability of serial data transfers.
"""


def check_sum(payload: bytes) -> int:
    """
    Calculate CRC-16/MODBUS checksum for the payload data.

    This function computes the CRC-16/Modbus checksum according to the standard algorithm used in
    many industrial communication protocols. The polynomial used is 0xA001, which is typical for
    CRC-16/Modbus.

    Args:
        payload (bytes): Payload data for which the checksum needs to be calculated.

    Returns:
        int: The computed CRC-16/Modbus checksum.

    Algorithm:
        - Initial value: 0xFFFF
        - XOR each byte with the current checksum value.
        - Shift right by one bit and XOR with 0xA001 if the least significant bit is set.
        - Repeat until all bytes have been processed.

    Notes:
        - This implementation follows the standard CRC-16/Modbus algorithm, widely used
          in protocols like Modbus RTU.
        - The returned checksum is a 16-bit unsigned integer.
    """
    cs = 0xFFFF
    for data_byte in payload:
        cs ^= data_byte
        for _ in range(8):
            if cs & 0x0001:
                cs = (cs >> 1) ^ 0xA001
            else:
                cs = cs >> 1
    return cs


def lrc(payload: bytes) -> int:
    """
    Calculate LRC (Longitudinal Redundancy Check) for the payload data.

    LRC is a simple yet effective checksum mechanism often used in serial communication protocols.
    It calculates the sum of all bytes modulo 256 and then inverts the result.

    Args:
        payload (bytes): Payload data for which the LRC needs to be calculated.

    Returns:
        int: The computed LRC value.

    Algorithm:
        - Sum all bytes in the payload.
        - Invert the sum using XOR with 0xFF.
        - Increment the inverted sum by 1.
        - Apply a mask of 0xFF to ensure the result fits within one byte.

    Notes:
        - LRC is less computationally intensive compared to CRC,
          but provides weaker error detection.
    """
    cs: int = 0
    for data_byte in payload:
        cs += int(data_byte)
    cs = ((cs ^ 0xFF) + 1) & 0xFF
    return cs


def check_lrc(message: bytes) -> bool:
    """
    Verify the correctness of the LRC byte at the end of the message.

    This function extracts the last byte of the message (assumed to be the LRC byte)
    and compares it against the computed LRC of the rest of the message. If they match,
    the LRC is considered valid.

    Args:
        message (bytes): Full message including the LRC byte at the end.

    Returns:
        bool: True if the LRC byte is correct, False otherwise.

    Notes:
        - If the message is malformed (e.g., too short), the function returns False.
        - Assumes the last byte of the message is the LRC byte.
    """
    try:
        cs: int = message[-1]
        payload: bytes = message[:-1]
        if lrc(payload) == cs:
            return True
    except IndexError:
        pass
    return False
