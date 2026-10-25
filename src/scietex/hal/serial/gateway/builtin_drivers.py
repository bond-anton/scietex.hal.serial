"""
Built-in Modbus driver descriptors.

These are the drivers this package itself provides: standard Modbus devices
that need no custom decoder, PDU, or translator. They are advertised through the
``scietex.modbus.drivers`` entry point group declared in ``pyproject.toml``.
"""

from .drivers import ModbusDriver

scietex_ftmone = ModbusDriver(
    name="scietex_ftmone",
    label="Scietex FtmOne",
    description="Scietex ftmONE film thickness monitor speaking standard Modbus RTU.",
    device_type="Film Thickness Monitor",
    framer="RTU",
    decoder=None,
    pdus=[],
    translator=None,
)

cyky_tm106b = ModbusDriver(
    name="cyky_tm106b",
    label="CYKY TM106B",
    description="CYKY TM106B film thickness monitor speaking standard Modbus ASCII.",
    device_type="Film Thickness Monitor",
    framer="ASCII",
    decoder=None,
    pdus=[],
    translator=None,
)
