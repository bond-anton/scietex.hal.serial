"""
Modbus driver registry.

Drivers are advertised through the ``scietex.modbus.drivers`` entry point group.
The group name is protocol-level rather than tied to a hosting package, so the
registry can move without breaking plugin declarations.

A driver descriptor names the four gateway plugin references a device needs
(framer, decoder, PDUs, translator). ``verify_driver`` resolves them exactly as
``GatewayDeviceConfig.__post_init__`` does, so "available" means "the gateway
would accept a device using this driver".

Entry points are read from installed distribution metadata. A driver added to a
source tree only appears after the package is reinstalled.

Functions:
    - discover_drivers: Map every advertised driver's name to its descriptor.
    - resolve_driver: Look up one descriptor by name.
    - verify_driver: Check that a descriptor's references resolve.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points

from .exceptions import GatewayConfigError
from .plugin_loader import (
    resolve_decoder,
    resolve_framer,
    resolve_pdu,
    resolve_translator,
)

ENTRY_POINT_GROUP = "scietex.modbus.drivers"


@dataclass(frozen=True, slots=True)
class ModbusDriver:
    """
    One advertised Modbus driver.

    Attributes:
        name (str): Entry point name, e.g. ``"thyracont_rs485_v1"``.
        label (str): Human-readable name shown in the UI.
        description (str): One-line description shown in the UI.
        device_type (str): Free-form device type label, e.g. ``"Vacuum Gauge"``.
        framer (str): Framer shortcut (``"RTU"``/``"ASCII"``) or dotted path.
        decoder (str | None): Dotted path to a custom decoder, or None.
        pdus (list[str]): Dotted paths to custom PDU classes to register.
        translator (str | None): Dotted path to a `GatewayTranslator`, or None.
    """

    name: str
    label: str
    description: str
    device_type: str
    framer: str
    decoder: str | None
    pdus: list[str]
    translator: str | None


def discover_drivers(entries: Iterable[EntryPoint] | None = None) -> dict[str, ModbusDriver]:
    """
    Map every advertised driver's entry point name to its descriptor.

    Args:
        entries (Iterable[EntryPoint] | None): Entry points to read. Defaults to
            the installed ``scietex.modbus.drivers`` group; tests inject
            synthetic entries because installed metadata is install-time.

    Returns:
        dict[str, ModbusDriver]: Entry point name to descriptor, sorted by name.

    Raises:
        TypeError: If an entry point resolves to something that is not a
            `ModbusDriver`.
    """
    source = entries if entries is not None else entry_points(group=ENTRY_POINT_GROUP)
    discovered: dict[str, ModbusDriver] = {}
    for entry_point in source:
        driver = entry_point.load()
        if not isinstance(driver, ModbusDriver):
            raise TypeError(
                f"Entry point {entry_point.name!r} resolved to "
                f"{type(driver).__name__}, not a ModbusDriver"
            )
        discovered[entry_point.name] = driver
    return dict(sorted(discovered.items()))


def resolve_driver(name: str) -> ModbusDriver | None:
    """
    Resolve a single driver by entry point name.

    Args:
        name (str): Entry point name, e.g. ``"thyracont_rs485_v1"``.

    Returns:
        ModbusDriver | None: The descriptor, or ``None`` when no advertised
        driver carries that name.
    """
    return discover_drivers().get(name)


def verify_driver(driver: ModbusDriver) -> str | None:
    """
    Check that a descriptor's plugin references resolve.

    Mirrors ``GatewayDeviceConfig.__post_init__`` so a driver that passes here
    cannot fail at worker startup.

    Args:
        driver (ModbusDriver): The descriptor to check.

    Returns:
        str | None: The `GatewayConfigError` message on failure, ``None`` on
        success.
    """
    checks = [("framer", driver.framer, resolve_framer)]
    if driver.decoder is not None:
        checks.append(("decoder", driver.decoder, resolve_decoder))
    checks.extend(("pdu", pdu, resolve_pdu) for pdu in driver.pdus)
    if driver.translator is not None:
        checks.append(("translator", driver.translator, resolve_translator))
    for kind, reference, resolve in checks:
        try:
            resolve(reference)
        except GatewayConfigError as exc:
            return f"{kind} {reference!r}: {exc}"
    return None
