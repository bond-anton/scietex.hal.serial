"""Tests for the Modbus driver registry."""

from importlib.metadata import EntryPoint

import pytest

try:
    from src.scietex.hal.serial.gateway.drivers import (
        ENTRY_POINT_GROUP,
        ModbusDriver,
        discover_drivers,
        resolve_driver,
        verify_driver,
    )
except ModuleNotFoundError:
    from scietex.hal.serial.gateway.drivers import (
        ENTRY_POINT_GROUP,
        ModbusDriver,
        discover_drivers,
        resolve_driver,
        verify_driver,
    )


def _entry_point(name: str, value: str) -> EntryPoint:
    return EntryPoint(name=name, value=value, group=ENTRY_POINT_GROUP)


def _rtu_driver(name: str = "rtu_driver") -> ModbusDriver:
    return ModbusDriver(
        name=name,
        label="RTU Driver",
        description="d",
        device_type="Film Thickness Monitor",
        framer="RTU",
        decoder=None,
        pdus=[],
        translator=None,
    )


def test_entry_point_group_name():
    assert ENTRY_POINT_GROUP == "scietex.modbus.drivers"


def test_discover_drivers_reads_descriptors_sorted_by_name():
    entries = [
        _entry_point(
            "zeta",
            "tests.gateway.vendor_stub.drivers:zeta_driver",
        ),
        _entry_point(
            "alpha",
            "tests.gateway.vendor_stub.drivers:alpha_driver",
        ),
    ]
    discovered = discover_drivers(entries)
    assert list(discovered) == ["alpha", "zeta"]
    assert discovered["alpha"].label == "Alpha Driver"
    assert discovered["alpha"].framer == "RTU"


def test_discover_drivers_ignores_packages_without_the_group():
    assert discover_drivers([]) == {}


def test_discover_drivers_rejects_a_non_descriptor():
    entries = [_entry_point("bad", "tests.gateway.vendor_stub.drivers:not_a_driver")]
    with pytest.raises(TypeError):
        discover_drivers(entries)


def test_resolve_driver_returns_none_for_unknown_name():
    assert resolve_driver("no_such_driver") is None


def test_verify_driver_accepts_a_resolvable_descriptor():
    assert verify_driver(_rtu_driver()) is None


def test_verify_driver_reports_a_bad_framer():
    driver = ModbusDriver(
        name="bad",
        label="Bad",
        description="d",
        device_type="x",
        framer="SOCKET",
        decoder=None,
        pdus=[],
        translator=None,
    )
    message = verify_driver(driver)
    assert message is not None
    assert "framer" in message


def test_verify_driver_reports_a_bad_decoder():
    driver = ModbusDriver(
        name="bad",
        label="Bad",
        description="d",
        device_type="x",
        framer="RTU",
        decoder="pymodbus.framer.FramerRTU",
        pdus=[],
        translator=None,
    )
    message = verify_driver(driver)
    assert message is not None
    assert "decoder" in message


def test_verify_driver_reports_a_bad_pdu():
    driver = ModbusDriver(
        name="bad",
        label="Bad",
        description="d",
        device_type="x",
        framer="RTU",
        decoder=None,
        pdus=["pymodbus.framer.FramerRTU"],
        translator=None,
    )
    message = verify_driver(driver)
    assert message is not None
    assert "pdu" in message


def test_verify_driver_reports_a_bad_translator():
    driver = ModbusDriver(
        name="bad",
        label="Bad",
        description="d",
        device_type="x",
        framer="RTU",
        decoder=None,
        pdus=[],
        translator="pymodbus.framer.FramerRTU",
    )
    message = verify_driver(driver)
    assert message is not None
    assert "translator" in message
