# scietex.hal.serial
**scietex.hal.serial** is a comprehensive serial communication library designed to provide
a high-level interface for managing serial ports and facilitating communication with serial devices.
The package is structured into four main modules, each serving a distinct purpose:

- config: Simplifies the creation, storage, and serialization of serial port configurations.
- virtual: Enables the generation and management of virtual serial networks, ideal for testing 
  environments and overcoming hardware limitations.
- server: Implements a Modbus server to streamline communication between various
  devices and applications.
- client: Provides a Modbus client that can be customized to interact with a
  wide range of equipment.

## System Requirements

- **Python**: 3.9 or higher.
- **Operating Systems**: Compatible with **Linux** and **macOS**.

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
from scietex.hal.serial import (
  SerialConnectionConfig, ModbusSerialConnectionConfig
)

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

    vsn2.add(
        [SerialConnectionConfig(vsn1.serial_ports[0])]
    )

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
from scietex.hal.serial import VirtualSerialPair, RS485Server, RS485Client, ModbusSerialConnectionConfig

async def main():
    vsp = VirtualSerialPair()
    vsp.start()

    server_config = ModbusSerialConnectionConfig(vsp.serial_ports[0])
    client_config = ModbusSerialConnectionConfig(vsp.serial_ports[1])

    server = RS485Server(server_config)
    await server.start()

    client = RS485Client(client_config, address=1, label="My RS485 Device")
    data = await client.read_registers(0, count=10)
    print(f"Registers data: {data}")
    
    await client.write_register_float(register=0, value=3.14159, factor=100)
    data = await client.read_registers(0, count=10)
    print(f"Registers data: {data}")

    value = await client.read_register_float(register=0, factor=100)
    print(f"Read value: {value}")

    await server.stop()
    vsp.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Contribution
We welcome contributions to the project! Whether it's bug fixes, feature enhancements,
or documentation improvements, your input is valuable. Please feel free to submit
pull requests or open issues to discuss potential changes.

## License

This project is licensed under the MIT License. For more details, please refer
to the `LICENSE` file included in the repository.
