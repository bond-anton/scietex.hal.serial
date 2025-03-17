"""Test checksum calculation functions."""

import pytest

try:
    from src.scietex.hal.serial.utilities.checksum import check_sum, lrc, check_lrc
except ModuleNotFoundError:
    from scietex.hal.serial.utilities.checksum import check_sum, lrc, check_lrc


def test_check_sum():
    """Checksum calculation test"""
    payload = b""  # Empty payload
    expected_result = 0xFFFF
    assert check_sum(payload) == expected_result

    payload = b"\x01\x02\x03"  # Simple payload
    expected_result = 0x6161
    assert check_sum(payload) == expected_result

    payload = b"\xff\xaa\x55\x33\xcc"  # More complex payload
    expected_result = 0x7915
    assert check_sum(payload) == expected_result


def test_lrc():
    """Test LRC calculation"""
    payload = b""  # Empty payload
    expected_result = 0x00
    assert lrc(payload) == expected_result

    payload = b"\x01\x02\x03"  # Simple payload
    expected_result = 0xFA
    assert lrc(payload) == expected_result

    payload = b"\xff\xaa\x55\x33\xcc"  # More complex payload
    expected_result = 0x03
    assert lrc(payload) == expected_result


def test_check_lrc():
    """Test for LRC check function"""
    message = b"\x01\x02\x03\xfa"  # Correct message
    assert check_lrc(message) is True

    message = b"\x01\x02\x03\x05"  # Incorrect message
    assert check_lrc(message) is False

    message = b""  # Empty message
    assert check_lrc(message) is False


if __name__ == "__main__":
    pytest.main()
