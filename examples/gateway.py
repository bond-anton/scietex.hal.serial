"""Example of ModbusGateway usage.

Starts an RS485 server on one end of a virtual serial pair and a Modbus gateway with its TCP
front end on the other end, then connects a real Modbus/TCP client and reads and writes a holding
register through the gateway.
"""

import asyncio

from pymodbus.client import AsyncModbusTcpClient

from scietex.hal.serial import (
    GatewayConfig,
    GatewayDeviceConfig,
    GatewayTcpServer,
    ModbusGateway,
    ModbusSerialConnectionConfig,
    RS485Server,
    VirtualSerialPair,
)

GATEWAY_PORT = 15020


async def main() -> None:
    """Run a read/write round trip through the gateway."""
    vsp = VirtualSerialPair()
    vsp.start()

    device_server = RS485Server(ModbusSerialConnectionConfig(vsp.serial_ports[0], timeout=0.5))
    await device_server.start()

    config = GatewayConfig(
        serial=ModbusSerialConnectionConfig(vsp.serial_ports[1], timeout=0.5),
        host="127.0.0.1",
        port=GATEWAY_PORT,
        devices={1: GatewayDeviceConfig(device_id=1, framer="RTU")},
    )
    gateway = ModbusGateway(config)
    tcp_server = GatewayTcpServer(config, gateway)
    await gateway.start()
    await tcp_server.start()

    client = AsyncModbusTcpClient("127.0.0.1", port=GATEWAY_PORT, timeout=1)
    try:
        await client.connect()
        read = await client.read_holding_registers(address=0, count=5, device_id=1)
        print(f"Read holding registers: {read.registers}")

        await client.write_register(address=0, value=42, device_id=1)
        read = await client.read_holding_registers(address=0, count=5, device_id=1)
        print(f"Read holding registers after write: {read.registers}")
    finally:
        client.close()
        await tcp_server.stop()
        await gateway.stop()
        await device_server.stop()
        vsp.stop()


if __name__ == "__main__":
    asyncio.run(main())
