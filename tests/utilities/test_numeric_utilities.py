"""Test numeric functions."""

import pytest

try:
    from src.scietex.hal.serial.utilities.numeric import (
        ByteOrder,
        from_signed32,
        to_signed32,
        from_signed16,
        to_signed16,
        float_to_int,
        float_to_int16,
        float_to_int32,
        float_to_unsigned16,
        float_to_unsigned32,
        float_from_int,
        float_from_unsigned16,
        float_from_unsigned32,
        split_32bit,
        combine_32bit,
    )
except ModuleNotFoundError:
    from scietex.hal.serial.utilities.numeric import (
        ByteOrder,
        from_signed32,
        to_signed32,
        from_signed16,
        to_signed16,
        float_to_int,
        float_to_int16,
        float_to_int32,
        float_to_unsigned16,
        float_to_unsigned32,
        float_from_int,
        float_from_unsigned16,
        float_from_unsigned32,
        split_32bit,
        combine_32bit,
    )


def test_from_signed32() -> None:
    """
    Test from_signed32 function.
    """
    # Positive values
    assert from_signed32(0x7FFFFFFF) == 2147483647  # Max positive 32-bit signed
    assert from_signed32(0x00000001) == 1  # Smallest positive
    assert from_signed32(0x00000000) == 0  # Zero

    # Negative values
    assert from_signed32(-1) == 0xFFFFFFFF  # -1
    assert from_signed32(-2147483648) == 0x80000000  # Min negative 32-bit signed
    assert from_signed32(-2) == 0xFFFFFFFE


def test_to_signed32() -> None:
    """
    Test to_signed32 function.
    """
    # Positive values
    assert to_signed32(0x7FFFFFFF) == 2147483647  # Max positive 32-bit signed
    assert to_signed32(0x00000001) == 1  # Smallest positive
    assert to_signed32(0x00000000) == 0  # Zero

    # Negative values
    assert to_signed32(0xFFFFFFFF) == -1  # -1
    assert to_signed32(0x80000000) == -2147483648  # Min negative 32-bit signed
    assert to_signed32(0xFFFFFFFE) == -2  # -2


def test_from_signed16():
    """
    Test from_signed16 function.
    """
    # Positive values
    assert from_signed16(32767) == 0x7FFF  # Max positive 16-bit signed
    assert from_signed16(1) == 0x0001  # Smallest positive
    assert from_signed16(0) == 0x0000  # Zero

    # Negative values
    assert from_signed16(-1) == 0xFFFF  # -1
    assert from_signed16(-32768) == 0x8000  # Min negative 16-bit signed
    assert from_signed16(-2) == 0xFFFE  # -2


def test_to_signed16():
    """
    Test to_signed32 function.
    """
    # Positive values
    assert to_signed16(0x7FFF) == 32767  # Max positive 16-bit signed
    assert to_signed16(0x0001) == 1  # Smallest positive
    assert to_signed16(0x0000) == 0  # Zero

    # Negative values
    assert to_signed16(0xFFFF) == -1  # -1
    assert to_signed16(0x8000) == -32768  # Min negative 16-bit signed
    assert to_signed16(0xFFFE) == -2  # -2


def test_float_to_int():
    """Test float to int conversion"""
    assert float_to_int(3.14159, 100) == 314
    assert float_to_int(3.14, 0) == 0
    assert float_to_int(0, 100) == 0
    assert float_to_int(-3.14159, 100) == -314


def test_float_to_int16():
    """Test float to int16 conversion"""
    assert float_to_int16(3.14159, 100) == 314
    assert float_to_int16(3.14, 0) == 0
    assert float_to_int16(0, 100) == 0
    assert float_to_int16(-3.14159, 100) == -314


def test_float_to_int32():
    """Test float to int32 conversion"""
    assert float_to_int32(3.14159, 100) == 314
    assert float_to_int32(3.14, 0) == 0
    assert float_to_int32(0, 100) == 0
    assert float_to_int32(-3.14159, 100) == -314


def test_float_to_unsigned_int16():
    """Test float to unsigned int16 conversion"""
    assert float_to_unsigned16(3.14159, 100) == 314
    assert float_to_unsigned16(3.14, 0) == 0
    assert float_to_unsigned16(0, 100) == 0
    assert float_to_unsigned16(-0.01, 100) == 0xFFFF


def test_float_to_unsigned_int32():
    """Test float to unsigned int32 conversion"""
    assert float_to_unsigned32(3.14159, 100) == 314
    assert float_to_unsigned32(3.14, 0) == 0
    assert float_to_unsigned32(0, 100) == 0
    assert float_to_unsigned32(-0.01, 100) == 0xFFFFFFFF


def test_float_from_int():
    """Test integer to float conversion"""
    assert float_from_int(314, 100) == 3.14
    assert float_from_int(0, 100) == 0
    assert float_from_int(-314, 100) == -3.14
    with pytest.raises(ValueError):
        float_from_int(314, 0)


def test_float_from_unsigned16():
    """Test 16-bit unsigned integer to float conversion"""
    assert float_from_unsigned16(314, 100) == 3.14
    assert float_from_unsigned16(0, 100) == 0
    with pytest.raises(ValueError):
        float_from_unsigned16(314, 0)


def test_float_from_unsigned32():
    """Test 32-bit unsigned integer to float conversion"""
    assert float_from_unsigned32(314, 100) == 3.14
    assert float_from_unsigned32(0, 100) == 0
    with pytest.raises(ValueError):
        float_from_unsigned32(314, 0)


def test_split_32bit():
    """Test split_32bit function"""
    # test little endian
    result = split_32bit(0xABCD1234, ByteOrder.LITTLE_ENDIAN)
    expected_result = (0x1234, 0xABCD)
    assert result == expected_result
    # test big endian
    result = split_32bit(0xABCD1234, ByteOrder.BIG_ENDIAN)
    expected_result = (0xABCD, 0x1234)
    assert result == expected_result
    # test invalid input type
    with pytest.raises(TypeError):
        split_32bit("invalid")
    # test_invalid_byteorder_value(self):
    with pytest.raises(ValueError):
        split_32bit(0xABCD1234, "unknown")


def test_combine_32bit():
    """Test combine_32bit function"""
    # test little endian
    result = combine_32bit(0x1234, 0x5678, ByteOrder.LITTLE_ENDIAN)
    expected_result = 0x56781234
    assert result == expected_result
    # test big endian
    result = combine_32bit(0x1234, 0x5678, ByteOrder.BIG_ENDIAN)
    expected_result = 0x12345678
    assert result == expected_result
    # test invalid input type
    with pytest.raises(TypeError):
        combine_32bit("invalid", 0x5678)
    with pytest.raises(TypeError):
        combine_32bit(0x1234, "invalid")
    # test invalid byteorder value
    with pytest.raises(ValueError):
        combine_32bit(0x1234, 0x5678, "unknown")


if __name__ == "__main__":
    pytest.main()
