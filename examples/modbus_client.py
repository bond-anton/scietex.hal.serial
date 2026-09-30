"""Example of RS485Client class usage."""

import asyncio

from scietex.hal.serial import (
    ModbusSerialConnectionConfig,
    RS485Client,
    RS485Server,
    VirtualSerialPair,
)


async def main():
    """The main function"""
    vsp = VirtualSerialPair()
    vsp.start()

    server_config = ModbusSerialConnectionConfig(vsp.serial_ports[0])
    client_config = ModbusSerialConnectionConfig(vsp.serial_ports[1])

    server = RS485Server(server_config)
    await server.start()

    async with RS485Client(client_config, address=1, label="My RS485 Device") as client:
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
