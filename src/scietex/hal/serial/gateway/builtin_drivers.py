"""
Built-in Modbus driver descriptors.

These are the drivers this package itself provides: standard Modbus devices
that need no custom decoder, PDU, or translator. They are advertised through the
``scietex.modbus.drivers`` entry point group declared in ``pyproject.toml``.

A descriptor is built in when the device speaks plain Modbus and the gateway
needs no vendor code to route it. The vendor package that owns the device's HAL
client is a separate concern: ``scietex.hal.vfd`` ships the Intek and Vesper
clients, but their gateway descriptors live here because they are plain RTU.
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

intek_spe_b = ModbusDriver(
    name="intek_spe_b",
    label="Intek SPE-B",
    description="Intek SPE-B variable frequency drive speaking standard Modbus RTU.",
    device_type="Variable Frequency Drive",
    framer="RTU",
    decoder=None,
    pdus=[],
    translator=None,
)

vesper_e5_8200 = ModbusDriver(
    name="vesper_e5_8200",
    label="Vesper E5-8200",
    description="Vesper E5-8200 variable frequency drive speaking standard Modbus RTU.",
    device_type="Variable Frequency Drive",
    framer="RTU",
    decoder=None,
    pdus=[],
    translator=None,
)

vesper_e4_8400 = ModbusDriver(
    name="vesper_e4_8400",
    label="Vesper E4-8400",
    description=(
        "Vesper E4-8400 / E4-P8402 variable frequency drive speaking standard Modbus RTU."
    ),
    device_type="Variable Frequency Drive",
    framer="RTU",
    decoder=None,
    pdus=[],
    translator=None,
)
