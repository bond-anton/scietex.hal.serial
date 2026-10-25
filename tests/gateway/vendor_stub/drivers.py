"""Synthetic driver descriptors used to exercise the registry."""

try:
    from src.scietex.hal.serial.gateway.drivers import ModbusDriver
except ModuleNotFoundError:
    from scietex.hal.serial.gateway.drivers import ModbusDriver

alpha_driver = ModbusDriver(
    name="alpha",
    label="Alpha Driver",
    description="Synthetic alpha driver.",
    device_type="Film Thickness Monitor",
    framer="RTU",
    decoder=None,
    pdus=[],
    translator=None,
)

zeta_driver = ModbusDriver(
    name="zeta",
    label="Zeta Driver",
    description="Synthetic zeta driver.",
    device_type="Film Thickness Monitor",
    framer="ASCII",
    decoder=None,
    pdus=[],
    translator=None,
)

not_a_driver = "not a descriptor"
