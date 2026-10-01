"""Example of SerialConnectionConfig class usage."""

from scietex.hal.serial import ModbusSerialConnectionConfig, SerialConnectionConfig


def main() -> None:
    """Create and print a plain and a Modbus serial connection config."""
    ser_conf = SerialConnectionConfig(port="/dev/ttyS01")
    ser_conf.baudrate = 9600
    ser_conf.timeout = 1.0
    print(ser_conf)

    modbus_conf = ModbusSerialConnectionConfig(**ser_conf.to_dict())
    print(modbus_conf)


if __name__ == "__main__":
    main()
