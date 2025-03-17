"""
Utility functions to convert between signed and unsigned numbers.

This module provides various utility functions for converting between different numeric
representations, such as signed and unsigned integers, floating-point numbers, and byte-order
manipulations. These functions are particularly useful when working with low-level data formats
or network protocols that require precise control over binary data.

Enums:
    - ByteOrder: Represents endianness options for byte manipulation.

Functions:
    - to_signed32(n: int) -> int:
        Converts a 32-bit unsigned integer to its signed representation.
    - from_signed32(n: int) -> int:
        Converts a signed 32-bit integer to its unsigned representation.
    - to_signed16(n: int) -> int:
        Converts a 16-bit unsigned integer to its signed representation.
    - from_signed16(n: int) -> int:
        Converts a signed 16-bit integer to its unsigned representation.
    - float_to_int(f: float, factor: Union[int, float] = 100) -> int:
        Converts a float to an integer by multiplying it with a scaling factor.
    - float_to_int16(f: float, factor: Union[int, float] = 100) -> int:
        Converts a float to a 16-bit signed integer by applying a scaling factor.
    - float_to_int32(f: float, factor: Union[int, float] = 100) -> int:
        Converts a float to a 32-bit signed integer by applying a scaling factor.
    - float_to_unsigned16(f: float, factor: Union[int, float] = 100) -> int:
        Converts a float to a 16-bit unsigned integer by applying a scaling factor.
    - float_to_unsigned32(f: float, factor: Union[int, float] = 100) -> int:
        Converts a float to a 32-bit unsigned integer by applying a scaling factor.
    - float_from_int(n: int, factor: Union[int, float] = 100) -> float:
        Converts an integer to a float by dividing it by a scaling factor.
    - float_from_unsigned16(n: int, factor: Union[int, float] = 100) -> float:
        Converts a 16-bit unsigned integer to a float by applying a scaling factor.
    - float_from_unsigned32(n: int, factor: Union[int, float] = 100) -> float:
        Converts a 32-bit unsigned integer to a float by applying a scaling factor.
    - split_32bit(n: int, byteorder: ByteOrder = ByteOrder.LITTLE_ENDIAN) -> Tuple[int, int]:
        Splits a 32-bit integer into two 16-bit values based on endianness.
    - combine_32bit(a: int, b: int, byteorder: ByteOrder = ByteOrder.LITTLE_ENDIAN) -> int:
        Combines two 16-bit values into a single 32-bit integer based on endianness.

These functions simplify working with numeric data across different platforms and systems,
reducing the chance of errors due to incorrect conversions or endianness mismatches.
"""

from typing import Union, Tuple
from enum import Enum


class ByteOrder(Enum):
    """
    Byte order enumeration.

    Represents endianness options for byte manipulation. Endianness determines the order in which
    bytes are stored in memory or transmitted over networks.

    Options:
        - LITTLE_ENDIAN ('le'): Least significant byte comes first.
        - BIG_ENDIAN ('be'): Most significant byte comes first.
    """

    LITTLE_ENDIAN = "le"
    BIG_ENDIAN = "be"


def to_signed32(n: int) -> int:
    """
    Convert a 32-bit unsigned integer to its signed representation.

    This function takes a 32-bit unsigned integer and converts it to its equivalent signed form,
    interpreting the most significant bit as the sign bit.

    Args:
        n (int): Input 32-bit unsigned integer.

    Returns:
        int: Signed 32-bit integer representation.

    Notes:
        - Ensures that the input is treated as a 32-bit value using a bitmask.
        - Interprets the highest bit (31st bit) as the sign bit.
    """
    n &= 0xFFFFFFFF  # Ensure 32-bit
    if n & 0x80000000:
        return n - 0x100000000
    return n


def from_signed32(n: int) -> int:
    """
    Convert a signed 32-bit integer to its unsigned representation.

    This function strips away the sign bit interpretation and treats the input as a pure 32-bit
    unsigned integer.

    Args:
        n (int): Input signed 32-bit integer.

    Returns:
        int: Unsigned 32-bit integer representation.

    Notes:
        - Ensures that the output is interpreted as a 32-bit unsigned value.
    """
    return n & 0xFFFFFFFF


def to_signed16(n: int) -> int:
    """
    Convert a 16-bit unsigned integer to its signed representation.

    This function takes a 16-bit unsigned integer and converts it to its equivalent signed form,
    interpreting the most significant bit as the sign bit.

    Args:
        n (int): Input 16-bit unsigned integer.

    Returns:
        int: Signed 16-bit integer representation.

    Notes:
        - Ensures that the input is treated as a 16-bit value using a bitmask.
        - Interprets the highest bit (15th bit) as the sign bit.
    """
    n = n & 0xFFFF  # Ensure 16-bit
    if n & 0x8000:
        return n - 0x10000
    return n


def from_signed16(n: int) -> int:
    """
    Convert a signed 16-bit integer to its unsigned representation.

    This function strips away the sign bit interpretation and treats the input as a pure 16-bit
    unsigned integer.

    Args:
        n (int): Input signed 16-bit integer.

    Returns:
        int: Unsigned 16-bit integer representation.

    Notes:
        - Ensures that the output is interpreted as a 16-bit unsigned value.
    """
    return n & 0xFFFF


def float_to_int(f: float, factor: Union[int, float] = 100) -> int:
    """
    Convert float to integer multiplied by a factor.

    Scales a floating-point number by multiplying it with a factor before rounding to the nearest
    integer. Useful for precision adjustments when working with fractional values.

    Args:
        f (float): Input floating-point number.
        factor (Union[int, float], optional): Scaling factor applied to the float.
            Defaults to 100.

    Returns:
        int: Integer representation of the scaled float.

    Notes:
        - Rounds the scaled value to the nearest integer using Python's built-in `round()`
          function.
    """
    return int(round(f * factor))


def float_to_int16(f: float, factor: Union[int, float] = 100) -> int:
    """
    Convert float to 16-bit signed integer multiplied by a factor.

    Scales a floating-point number by multiplying it with a factor before rounding to the nearest
    integer and converting it to a 16-bit signed format.

    Args:
        f (float): Input floating-point number.
        factor (Union[int, float], optional): Scaling factor applied to the float. Defaults to 100.

    Returns:
        int: 16-bit signed integer representation of the scaled float.

    Notes:
        - Applies `to_signed16()` to enforce 16-bit signedness.
    """
    return to_signed16(float_to_int(f, factor))


def float_to_int32(f: float, factor: Union[int, float] = 100) -> int:
    """
    Convert float to 32-bit signed integer multiplied by a factor.

    Scales a floating-point number by multiplying it with a factor before rounding to the nearest
    integer and converting it to a 32-bit signed format.

    Args:
        f (float): Input floating-point number.
        factor (Union[int, float], optional): Scaling factor applied to the float. Defaults to 100.

    Returns:
        int: 32-bit signed integer representation of the scaled float.

    Notes:
        - Applies `to_signed32()` to enforce 32-bit signedness.
    """
    return to_signed32(float_to_int(f, factor))


def float_to_unsigned16(f: float, factor: Union[int, float] = 100) -> int:
    """
    Convert float to unsigned 16-bit integer multiplied by a factor.

    Scales a floating-point number by multiplying it with a factor before rounding to the nearest
    integer and converting it to a 16-bit unsigned format.

    Args:
        f (float): Input floating-point number.
        factor (Union[int, float], optional): Scaling factor applied to the float. Defaults to 100.

    Returns:
        int: 16-bit unsigned integer representation of the scaled float.

    Notes:
        - Applies `from_signed16()` to enforce 16-bit unsignedness.
    """
    return from_signed16(float_to_int(f, factor))


def float_to_unsigned32(f: float, factor: Union[int, float] = 100) -> int:
    """
    Convert float to unsigned 32-bit integer multiplied by a factor.

    Scales a floating-point number by multiplying it with a factor before rounding to the nearest
    integer and converting it to a 32-bit unsigned format.

    Args:
        f (float): Input floating-point number.
        factor (Union[int, float], optional): Scaling factor applied to the float. Defaults to 100.

    Returns:
        int: 32-bit unsigned integer representation of the scaled float.

    Notes:
        - Applies `from_signed32()` to enforce 32-bit unsignedness.
    """
    return from_signed32(float_to_int(f, factor))


def float_from_int(n: int, factor: Union[int, float] = 100) -> float:
    """
    Convert integer to float divided by a factor.

    Divides an integer by a scaling factor to recover the original floating-point representation.

    Args:
        n (int): Input integer.
        factor (Union[int, float], optional): Scaling factor applied to the float. Defaults to 100.

    Returns:
        float: Floating-point representation of the scaled integer.

    Raises:
        ValueError: If the scaling factor is zero, division by zero would occur.

    Notes:
        - Checks for a non-zero factor to avoid potential division-by-zero errors.
    """
    if factor == 0:
        raise ValueError("Factor cannot be zero.")
    return n / factor


def float_from_unsigned16(n: int, factor: Union[int, float] = 100) -> float:
    """
    Convert 16-bit unsigned integer to float divided by a factor.

    Recovers a floating-point number from a 16-bit unsigned integer by treating it as a signed
    integer and dividing by a scaling factor.

    Args:
        n (int): Input 16-bit unsigned integer.
        factor (Union[int, float], optional): Scaling factor applied to the float. Defaults to 100.

    Returns:
        float: Floating-point representation of the scaled unsigned integer.

    Raises:
        ValueError: If the scaling factor is zero, division by zero would occur.

    Notes:
        - Treats the input as a signed 16-bit integer using `to_signed16()` before conversion.
    """
    if factor == 0:
        raise ValueError("Factor cannot be zero.")
    return to_signed16(n) / factor


def float_from_unsigned32(n: int, factor: Union[int, float] = 100) -> float:
    """
    Convert 32-bit unsigned integer to float divided by a factor.

    Recovers a floating-point number from a 32-bit unsigned integer by treating it as a signed
    integer and dividing by a scaling factor.

    Args:
        n (int): Input 32-bit unsigned integer.
        factor (Union[int, float], optional): Scaling factor applied to the float. Defaults to 100.

    Returns:
        float: Floating-point representation of the scaled unsigned integer.

    Raises:
        ValueError: If the scaling factor is zero, division by zero would occur.

    Notes:
        - Treats the input as a signed 32-bit integer using `to_signed32()` before conversion.
    """
    if factor == 0:
        raise ValueError("Factor cannot be zero.")
    return to_signed32(n) / factor


def split_32bit(
    n: int, byteorder: ByteOrder = ByteOrder.LITTLE_ENDIAN
) -> Tuple[int, int]:
    """
    Split 32-bit integer between two 16-bit values.

    Breaks down a 32-bit integer into two 16-bit values based on the specified byte order.

    Args:
        n (int): Input 32-bit integer.
        byteorder (ByteOrder, optional): Endianness option. Defaults to little-endian.

    Returns:
        Tuple[int, int]: Two 16-bit integers representing the lower and upper halves of the input.

    Raises:
        TypeError: If the input is not an integer.
        ValueError: If the byteorder argument is invalid.

    Notes:
        - Uses bitwise operations to extract the lower and upper 16-bit portions of the 32-bit
          integer.
        - Respects endianness when splitting the integer.
    """
    if not isinstance(n, int):
        raise TypeError("Invalid type of input")
    if byteorder == ByteOrder.BIG_ENDIAN:
        return (n & 0xFFFFFFFF) >> 16, n & 0xFFFF
    if byteorder == ByteOrder.LITTLE_ENDIAN:
        return n & 0xFFFF, (n & 0xFFFFFFFF) >> 16
    raise ValueError("Invalid byteorder value")


def combine_32bit(
    a: int, b: int, byteorder: ByteOrder = ByteOrder.LITTLE_ENDIAN
) -> int:
    """
    Combine 32-bit integer from two 16-bit values.

    Constructs a 32-bit integer from two 16-bit values based on the specified byte order.

    Args:
        a (int): Lower 16-bit portion of the resulting 32-bit integer.
        b (int): Upper 16-bit portion of the resulting 32-bit integer.
        byteorder (ByteOrder, optional): Endianness option. Defaults to little-endian.

    Returns:
        int: Combined 32-bit integer.

    Raises:
        TypeError: If either input is not an integer.
        ValueError: If the byteorder argument is invalid.

    Notes:
        - Uses bitwise operations to construct the 32-bit integer.
        - Respects endianness when combining the 16-bit values.
    """
    if not isinstance(a, int) or not isinstance(b, int):
        raise TypeError("Invalid type of input")
    if byteorder == ByteOrder.LITTLE_ENDIAN:
        return ((b & 0xFFFF) << 16) + (a & 0xFFFF)
    if byteorder == ByteOrder.BIG_ENDIAN:
        return ((a & 0xFFFF) << 16) + (b & 0xFFFF)
    raise ValueError("Invalid byteorder value")
