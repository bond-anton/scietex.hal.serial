# scietex.hal.serial

**scietex.hal.serial** is a serial communication library for Python. It provides a
high-level interface for managing serial ports and for talking to Modbus/RS485
devices, plus a virtual serial layer that lets you test the whole stack without
hardware.

## What's inside

| Module | Purpose |
| --- | --- |
| [`config`](api/config.md) | Serial connection configuration dataclasses, validation, and serialization. |
| [`virtual`](api/virtual.md) | Virtual serial pairs and networks backed by PTYs — hardware-free testing. |
| [`server`](api/server.md) | A Modbus/RS485 server with a reactive datastore. |
| [`client`](api/client.md) | A Modbus/RS485 client with typed read/write helpers. |
| [`gateway`](api/gateway.md) | A serial↔TCP Modbus gateway that routes by device id and supports non-Modbus vendor protocols. |
| [`utilities`](api/utilities.md) | Checksums, numeric helpers, Modbus helpers, and serial-port discovery. |

## Requirements

- **Python**: 3.10 or higher.
- **Operating systems**: Linux and macOS. The virtual serial layer uses
  `pty.openpty` and `multiprocessing`, so it does not run on Windows.

## Installation

```bash
pip install scietex.hal.serial
```

## Quick start

```python
import asyncio

from scietex.hal.serial import (
    ModbusSerialConnectionConfig,
    RS485Client,
    RS485Server,
    VirtualSerialPair,
)


async def main():
    vsp = VirtualSerialPair()
    vsp.start()

    server = RS485Server(ModbusSerialConnectionConfig(vsp.serial_ports[0]))
    await server.start()

    async with RS485Client(ModbusSerialConnectionConfig(vsp.serial_ports[1]), address=1) as client:
        await client.write_register_float(register=0, value=3.14159, factor=100)
        print(await client.read_register_float(register=0, factor=100))

    await server.stop()
    vsp.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

## Where to go next

- New to the library? Start with the [User Guide](guide/configuration.md).
- Upgrading from 1.x? Read [Upgrading to 2.0](guide/upgrading.md).
- Looking for a specific class or function? See the [API Reference](api/index.md).
- Curious how it is built? See the [Architecture](architecture/README.md) map.
