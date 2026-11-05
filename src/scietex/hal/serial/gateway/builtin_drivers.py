"""
Built-in Modbus driver descriptors.

A descriptor names the four gateway plugin references a device needs (framer,
decoder, PDUs, translator). These two are the protocol shapes this package
itself provides: plain Modbus over RTU or ASCII, with no custom decoder, PDU, or
translator. They are advertised through the ``scietex.modbus.drivers`` entry
point group declared in ``pyproject.toml``.

A device that speaks plain Modbus needs nothing beyond its framing, so it picks
one of these two and carries its own identity in the device name. A descriptor
of its own would repeat the same four empty fields under a vendor label. Vendor
packages are only involved when the gateway must import their code to route a
device — a translator, a custom framer, or custom PDUs — and those descriptors
live in the vendor package and are installed as an extra.
"""

from .drivers import ModbusDriver

standard_rtu = ModbusDriver(
    name="standard_rtu",
    label="Standard Modbus RTU",
    description="Any device speaking plain Modbus RTU. The default for a serial bus.",
    device_type="Modbus Device",
    framer="RTU",
    decoder=None,
    pdus=[],
    translator=None,
)

standard_ascii = ModbusDriver(
    name="standard_ascii",
    label="Standard Modbus ASCII",
    description="Any device speaking plain Modbus ASCII.",
    device_type="Modbus Device",
    framer="ASCII",
    decoder=None,
    pdus=[],
    translator=None,
)
