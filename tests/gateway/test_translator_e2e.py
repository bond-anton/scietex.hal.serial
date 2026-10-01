"""
End-to-end test of the non-standard (translator) path.

A standard Modbus/TCP client reads holding registers through the gateway; the
gateway translates FC03 into the synthetic vendor ``"R"`` command, sends it over
a virtual serial pair to a vendor emulator, and translates the response back.

The vendor plugin lives in ``tests/gateway/vendor_stub`` and is resolved by
dotted path, exactly as a real plugin package would be.
"""

import socket

import pytest
from pymodbus.client import AsyncModbusTcpClient

from scietex.hal.serial.config import ModbusSerialConnectionConfig
from scietex.hal.serial.gateway.config import GatewayConfig, GatewayDeviceConfig
from scietex.hal.serial.gateway.gateway import ModbusGateway
from scietex.hal.serial.gateway.tcp_server import GatewayTcpServer
from tests.gateway.vendor_stub.emulator import VendorEmulator

# Dotted paths to the synthetic plugin artifacts. `tests/` is a namespace
# package, so these resolve from the repo root (pytest.ini sets pythonpath = .).
_PDU = "tests.gateway.vendor_stub.pdu.VendorRequest"
_FRAMER = "tests.gateway.vendor_stub.framer.VendorFramer"
_DECODER = "tests.gateway.vendor_stub.decoder.VendorDecodePDU"
_TRANSLATOR = "tests.gateway.vendor_stub.translator.VendorTranslator"


def _free_port() -> int:
    """Pick a free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def vendor_device(vsp_fixture, logger_fixture):
    """A synthetic vendor emulator on one end of the virtual pair."""
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[0], timeout=0.5)
    return VendorEmulator(serial, address=1, logger=logger_fixture)


@pytest.fixture
def gateway_stack(vsp_fixture, logger_fixture):
    """A started gateway + TCP server wired to the vendor plugin."""
    port = _free_port()
    serial = ModbusSerialConnectionConfig(vsp_fixture.serial_ports[1], timeout=0.5)
    config = GatewayConfig(
        serial=serial,
        host="127.0.0.1",
        port=port,
        devices={
            1: GatewayDeviceConfig(
                device_id=1,
                framer=_FRAMER,
                decoder=_DECODER,
                pdus=[_PDU],
                translator=_TRANSLATOR,
            )
        },
    )
    gateway = ModbusGateway(config, logger=logger_fixture)
    server = GatewayTcpServer(config, gateway, logger=logger_fixture)
    return gateway, server, port


@pytest.mark.asyncio
async def test_translator_end_to_end(vendor_device, gateway_stack):
    """A standard FC03 read is translated to the vendor command and back."""
    gateway, server, port = gateway_stack
    await vendor_device.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        response = await client.read_holding_registers(address=0, count=1, device_id=1)
        assert not response.isError()
        assert response.registers == [1234]
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await vendor_device.stop()


@pytest.mark.asyncio
async def test_translator_second_register(vendor_device, gateway_stack):
    """A different register address maps to a different vendor value."""
    gateway, server, port = gateway_stack
    await vendor_device.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        response = await client.read_holding_registers(address=1, count=1, device_id=1)
        assert not response.isError()
        assert response.registers == [5678]
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await vendor_device.stop()


@pytest.mark.asyncio
async def test_translator_multiple_requests(vendor_device, gateway_stack):
    """Repeated translated requests over one connection all succeed."""
    gateway, server, port = gateway_stack
    await vendor_device.start()
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        for _ in range(3):
            response = await client.read_holding_registers(address=0, count=1, device_id=1)
            assert not response.isError()
            assert response.registers == [1234]
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
        await vendor_device.stop()


@pytest.mark.asyncio
async def test_translator_bus_failure_maps_to_exception(gateway_stack):
    """With no vendor device running, the client gets a Modbus exception."""
    gateway, server, port = gateway_stack
    await gateway.start()
    await server.start()
    client = AsyncModbusTcpClient("127.0.0.1", port=port, timeout=1)
    try:
        await client.connect()
        response = await client.read_holding_registers(address=0, count=1, device_id=1)
        assert response.isError()
    finally:
        client.close()
        await server.stop()
        await gateway.stop()
