"""Example of SerialConnectionConfig class usage."""

from scietex.hal.serial import SerialConnectionConfig, ModbusSerialConnectionConfig

ser_conf = SerialConnectionConfig(port="/dev/ttyS01")
ser_conf.baudrate = 9600
ser_conf.timeout = 1.0
print(ser_conf)

modbus_conf = ModbusSerialConnectionConfig(**ser_conf.to_dict())
print(modbus_conf)
