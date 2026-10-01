"""Test serial port finder utilities."""

from types import SimpleNamespace
from unittest.mock import patch

try:
    from src.scietex.hal.serial.utilities.serial_port_finder import (
        find_rs485,
        find_serial_ports,
        find_stm32_cdc,
    )
except ModuleNotFoundError:
    from scietex.hal.serial.utilities.serial_port_finder import (
        find_rs485,
        find_serial_ports,
        find_stm32_cdc,
    )


def _comports(*ports: SimpleNamespace) -> list[SimpleNamespace]:
    return list(ports)


def test_find_serial_ports_matches_vid_and_pid():
    ports = _comports(
        SimpleNamespace(vid=0x0483, pid=0x5740, device="/dev/ttyACM0"),
        SimpleNamespace(vid=0x1A86, pid=0x7523, device="/dev/ttyUSB0"),
        SimpleNamespace(vid=0x0483, pid=0x9999, device="/dev/ttyACM1"),
        SimpleNamespace(vid=None, pid=None, device="/dev/ttyS0"),
    )
    with patch("serial.tools.list_ports.comports", return_value=ports):
        result = find_serial_ports({0x0483: [0x5740]})
    assert result == ["/dev/ttyACM0"]


def test_find_stm32_cdc_uses_default_profile():
    ports = _comports(
        SimpleNamespace(vid=0x0483, pid=0x5740, device="/dev/ttyACM0"),
        SimpleNamespace(vid=0x1A86, pid=0x7523, device="/dev/ttyUSB0"),
    )
    with patch("serial.tools.list_ports.comports", return_value=ports):
        result = find_stm32_cdc()
    assert result == ["/dev/ttyACM0"]


def test_find_rs485_uses_default_profile():
    ports = _comports(
        SimpleNamespace(vid=0x0483, pid=0x5740, device="/dev/ttyACM0"),
        SimpleNamespace(vid=0x1A86, pid=0x7523, device="/dev/ttyUSB0"),
    )
    with patch("serial.tools.list_ports.comports", return_value=ports):
        result = find_rs485()
    assert result == ["/dev/ttyUSB0"]


def test_find_stm32_cdc_override_mapping():
    ports = _comports(
        SimpleNamespace(vid=0x0483, pid=0x5740, device="/dev/ttyACM0"),
        SimpleNamespace(vid=0x1234, pid=0x5678, device="/dev/ttyCUSTOM"),
    )
    with patch("serial.tools.list_ports.comports", return_value=ports):
        result = find_stm32_cdc(mapping={0x1234: [0x5678]})
    assert result == ["/dev/ttyCUSTOM"]
