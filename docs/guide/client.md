# Modbus Client

`RS485Client` talks to a Modbus device over a serial port. It requires a
connection config and a slave address, and accepts an optional label for
readable logs.

## End-to-end example

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

## Lifecycle

Use the client as an async context manager (`async with`) so the serial port is
released deterministically. Constructing it directly also works, but then you
must call `await client.close()` yourself.

## Error handling

Read, write, and execute operations raise `ModbusOperationError` on failure by
default. See [Upgrading to 2.0](upgrading.md) for the full error contract and
how to opt out per call.

See the [Client API reference](../api/client.md) for the full method list.
