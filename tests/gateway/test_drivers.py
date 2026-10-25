"""Tests for the Modbus driver registry."""

from importlib.metadata import EntryPoint

import pytest

try:
    from scietex.hal.serial.gateway.drivers import (
        ENTRY_POINT_GROUP,
        ModbusDriver,
        discover_drivers,
        resolve_driver,
        verify_driver,
    )
except ModuleNotFoundError:
    from src.scietex.hal.serial.gateway.drivers import (
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


def test_discover_drivers_skips_an_entry_point_that_fails_to_load():
    entries = [
        _entry_point("broken", "tests.gateway.vendor_stub.drivers:missing_attribute"),
        _entry_point("alpha", "tests.gateway.vendor_stub.drivers:alpha_driver"),
    ]
    discovered = discover_drivers(entries)
    assert list(discovered) == ["alpha"]


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


def test_builtin_descriptors_are_well_formed():
    try:
        from scietex.hal.serial.gateway.builtin_drivers import (
            cyky_tm106b,
            scietex_ftmone,
        )
    except ModuleNotFoundError:
        from src.scietex.hal.serial.gateway.builtin_drivers import (
            cyky_tm106b,
            scietex_ftmone,
        )

    assert scietex_ftmone.name == "scietex_ftmone"
    assert scietex_ftmone.framer == "RTU"
    assert scietex_ftmone.decoder is None
    assert scietex_ftmone.pdus == []
    assert scietex_ftmone.translator is None
    assert scietex_ftmone.device_type == "Film Thickness Monitor"

    assert cyky_tm106b.name == "cyky_tm106b"
    assert cyky_tm106b.framer == "ASCII"
    assert cyky_tm106b.device_type == "Film Thickness Monitor"

    assert verify_driver(scietex_ftmone) is None
    assert verify_driver(cyky_tm106b) is None


def test_builtin_drivers_are_declared_as_entry_points():
    """The declarations are install-time; skip when metadata is stale."""
    from importlib.metadata import entry_points

    declared = {entry.name for entry in entry_points(group=ENTRY_POINT_GROUP)}
    if not declared:
        pytest.skip("installed metadata carries no scietex.modbus.drivers group")
    assert {"scietex_ftmone", "cyky_tm106b"} <= declared
