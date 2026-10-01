# scietex.hal.serial

**scietex.hal.serial** is a comprehensive serial communication library designed to provide
a high-level interface for managing serial ports and facilitating communication with serial devices.
The package is structured into six main modules, each serving a distinct purpose:

- config: Simplifies the creation, storage, and serialization of serial port configurations.
- virtual: Enables the generation and management of virtual serial networks, ideal for testing
  environments and overcoming hardware limitations.
- server: Implements a Modbus server to streamline communication between various
  devices and applications.
- client: Provides a Modbus client that can be customized to interact with a
  wide range of the equipment.
- gateway: Bridges a serial RS485 bus to TCP/IP, routing Modbus/TCP requests by device id and
  supporting non-Modbus vendor protocols through translator plugins.
- utilities: Checksums, numeric helpers, Modbus helpers, and serial-port discovery.

## Documentation

Full documentation is available at
**[scietex-hal-serial.readthedocs.io](https://scietex-hal-serial.readthedocs.io/)**,
covering the user guide, API reference, architecture, and design notes.

## System Requirements

- **Python**: 3.10 or higher.
- **Operating Systems**: Compatible with **Linux** and **macOS**. The virtual serial layer uses
  `pty.openpty` and `multiprocessing`, so it does not run on Windows.

## Installation

To install the package, execute the following command in your terminal:

```bash
pip install scietex.hal.serial
```

## Usage

### Serial Connection Configuration

Configuring a serial connection is straightforward. Here's how you can set it up:

```python
from scietex.hal.serial import SerialConnectionConfig

ser_conf = SerialConnectionConfig(port="/dev/ttyS01")
ser_conf.baudrate = 9600
```
For serialization purposes, you can convert the configuration to a dictionary:

```python
from scietex.hal.serial import SerialConnectionConfig, ModbusSerialConnectionConfig

ser_conf = SerialConnectionConfig(port="/dev/ttyS01")
ser_conf.baudrate = 9600
ser_conf.timeout = 1.0
print(ser_conf)

modbus_conf = ModbusSerialConnectionConfig(**ser_conf.to_dict())
print(modbus_conf)
```

### Virtual Serial Network
Creating a virtual serial network is simple.
Here's an example of creating a virtual serial pair:

```python
from scietex.hal.serial import VirtualSerialPair

if __name__ == "__main__":
    vsp = VirtualSerialPair()
    vsp.start()
    # Now your virtual serial pair is ready
    print(vsp.serial_ports)

    vsp.stop()
```

For more complex topologies, you can use the VirtualSerialNetwork class to connect multiple
virtual ports or even integrate with external physical ports:

```python
from scietex.hal.serial import VirtualSerialNetwork, SerialConnectionConfig

if __name__ == "__main__":
    vsn1 = VirtualSerialNetwork(virtual_ports_num=3)
    vsn1.start()
    print(f"VSN 1 ports: {vsn1.serial_ports}")

    vsn2 = VirtualSerialNetwork(virtual_ports_num=2)
    vsn2.start()

    vsn2.add([SerialConnectionConfig(vsn1.serial_ports[0])])

    # Create two more virtual ports
    vsn1.create(2)

    print(f"VSN 1 ports: {vsn1.serial_ports}")
    print(f"VSN 2 ports: {vsn2.serial_ports}")

    vsn1.stop()
    vsn2.stop()
```
### Modbus Server
To start a Modbus server, follow these steps:
```python
import asyncio
from scietex.hal.serial import RS485Server, ModbusSerialConnectionConfig


async def main():
    config = ModbusSerialConnectionConfig("/dev/ttyS001")
    server = RS485Server(config)
    await server.start()

    await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
```
The server supports multiple slaves, which can be added, updated, or removed dynamically.

### Modbus Client
The Modbus client requires a connection configuration and a slave address. Optionally,
you can provide a label for enhanced logging readability:

```python
import asyncio
from scietex.hal.serial import (
    VirtualSerialPair,
    RS485Server,
    RS485Client,
    ModbusSerialConnectionConfig,
)


async def main():
    vsp = VirtualSerialPair()
    vsp.start()

    server_config = ModbusSerialConnectionConfig(vsp.serial_ports[0])
    client_config = ModbusSerialConnectionConfig(vsp.serial_ports[1])

    server = RS485Server(server_config)
    await server.start()

    async with RS485Client(client_config, address=1, label="My RS485 Device") as client:
        data = await client.read_registers(0, count=10)
        print(f"Registers payload: {data}")

        await client.write_register_float(register=0, value=3.14159, factor=100)
        data = await client.read_registers(0, count=10)
        print(f"Registers payload: {data}")

        value = await client.read_register_float(register=0, factor=100)
        print(f"Read value: {value}")

    await server.stop()
    vsp.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

### Modbus Gateway

The gateway bridges a serial RS485 bus to TCP/IP. It owns one serial port,
accepts standard Modbus/TCP clients, and routes each request to the right device
on the bus by device id. Non-Modbus vendor devices are supported through a
translator plugin.

```python
import asyncio

from scietex.hal.serial import (
    GatewayConfig,
    GatewayDeviceConfig,
    ModbusGateway,
    ModbusSerialConnectionConfig,
)


async def main():
    config = GatewayConfig(
        serial=ModbusSerialConnectionConfig("/dev/ttyUSB0", baudrate=9600),
        host="0.0.0.0",
        port=502,
        default_framer="RTU",
        devices={
            1: GatewayDeviceConfig(device_id=1, framer="RTU"),
            2: GatewayDeviceConfig(device_id=2, framer="ASCII"),
        },
    )

    gateway = ModbusGateway(config)
    await gateway.start()

    # ... serve until shutdown ...

    await gateway.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

A TCP client then connects to `host:port` and issues normal Modbus/TCP requests
with the target device id as the unit id. See the
[Gateway guide](https://scietex-hal-serial.readthedocs.io/en/latest/guide/gateway/)
for configuration details and the non-standard protocol path.

### Upgrading to 2.0

Version 2.0 makes the error contract strict by default. Read, write, and execute
operations now raise `ModbusOperationError` on failure instead of returning `None`.

```python
from scietex.hal.serial import ModbusOperationError

try:
    value = await client.read_register(0)
except ModbusOperationError as exc:
    print(f"Read failed: {exc}")
```

- **Opt out per call.** Pass `raise_on_error=False` to restore the 1.x behavior of
  returning `None` on failure. The parameter exists on every read/write wrapper and
  `RS485Client` method, so you can migrate incrementally.
- **`None` is no longer a failure sentinel.** Stop using `if result is None` to detect
  failure; catch `ModbusOperationError` instead. `None` now only means "no response was
  expected" (`no_response_expected=True`).
- **Write→read fallback is opt-in.** In 1.x, a write whose response was falsy silently
  fell back to a read-back. That fallback now runs only when you pass
  `raise_on_error=False`. Devices that do not echo write responses must use
  `raise_on_error=False`; under that mode a `None` result means "unverifiable", not
  necessarily "failed".
- **`no_response_expected=True` is unchanged.** It still returns `None` and never raises.
- **Subclass authors.** Overrides of `read_data`/`process_message` that call `read_*`
  methods will now propagate `ModbusOperationError` unless each inner call passes
  `raise_on_error=False`.

## Contribution
We welcome contributions to the project! Whether it's bug fixes, feature enhancements,
or documentation improvements, your input is valuable. Please feel free to submit
pull requests or open issues to discuss potential changes.

## License

This project is licensed under the MIT License. For more details, please refer
to the `LICENSE` file included in the repository.
