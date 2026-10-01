# Configuration

Serial connections are described by dataclasses in the `config` module. They
validate their fields on construction and can be serialized to and from plain
dictionaries.

## Basic serial connection

```python
from scietex.hal.serial import SerialConnectionConfig

ser_conf = SerialConnectionConfig(port="/dev/ttyS01")
ser_conf.baudrate = 9600
```

## Serialization

`to_dict()` produces a plain dictionary that can be fed back into any of the
config classes:

```python
from scietex.hal.serial import SerialConnectionConfig, ModbusSerialConnectionConfig

ser_conf = SerialConnectionConfig(port="/dev/ttyS01")
ser_conf.baudrate = 9600
ser_conf.timeout = 1.0
print(ser_conf)

modbus_conf = ModbusSerialConnectionConfig(**ser_conf.to_dict())
print(modbus_conf)
```

## The three config classes

| Class | Adds |
| --- | --- |
| `SerialConnectionMinimalConfig` | Port and baudrate only. |
| `SerialConnectionConfig` | Full serial parameters (bytesize, parity, stopbits, timeout, ...). |
| `ModbusSerialConnectionConfig` | Adds Modbus framing (`framer`) on top of `SerialConnectionConfig`. |

All three raise `SerialConnectionConfigError` on invalid input. See the
[Configuration API reference](../api/config.md) for the full field list.
