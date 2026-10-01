# Modbus Server

`RS485Server` runs a Modbus server on a serial port. It answers from a
`ReactiveSequentialDataBlock`, which lets you react to register writes.

## Starting a server

```python
import asyncio

from scietex.hal.serial import ModbusSerialConnectionConfig, RS485Server


async def main():
    config = ModbusSerialConnectionConfig("/dev/ttyS001")
    server = RS485Server(config)
    await server.start()

    await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

## Multiple slaves

The server supports multiple slaves, which can be added, updated, or removed
dynamically while it is running.

## Reacting to writes

`ReactiveSequentialDataBlock` is a datastore block that calls a callback when a
register is written. Use it to drive application logic from Modbus writes.

See the [Server API reference](../api/server.md) for the full interface.
