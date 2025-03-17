"""Example of RS485Server class usage."""

import asyncio
from scietex.hal.serial import (
    VirtualSerialPair,
    RS485Server,
    ModbusSerialConnectionConfig,
)


async def main():
    """The main function"""
    vsp = VirtualSerialPair()
    vsp.start()
    config = ModbusSerialConnectionConfig(vsp.serial_ports[0])
    server = RS485Server(config)
    await server.start()
    # Now the server is running
    await server.stop()
    vsp.stop()


if __name__ == "__main__":
    asyncio.run(main())
