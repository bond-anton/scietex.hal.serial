"""Stale-response regression tests on a real pty transport.

These tests exercise pymodbus's ``SerialTransport``/``TransactionManager`` end
to end instead of mocking ``ModbusGateway._bus.execute``. A raw RTU responder on
the far end of the virtual pair answers the first request *after* the gateway's
hold budget has expired. RTU frames carry no usable transaction id (it is always
0) and are matched by device id only, so that late reply is indistinguishable
from the answer to the next request unless the gateway resynchronizes the bus
first.
"""

import asyncio
import threading
import time

import pytest
import serial
from pymodbus.pdu import ExceptionResponse
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersRequest,
    ReadHoldingRegistersResponse,
)

try:
    from src.scietex.hal.serial.config import ModbusSerialConnectionConfig
    from src.scietex.hal.serial.gateway.config import GatewayConfig, GatewayDeviceConfig
    from src.scietex.hal.serial.gateway.gateway import ModbusGateway
except ModuleNotFoundError:
    from scietex.hal.serial.config import ModbusSerialConnectionConfig
    from scietex.hal.serial.gateway.config import GatewayConfig, GatewayDeviceConfig
    from scietex.hal.serial.gateway.gateway import ModbusGateway

# FC03 request: device id, function, address (2 bytes), count (2 bytes), CRC.
_REQUEST_SIZE = 8


def _crc16(data: bytes) -> int:
    """Modbus RTU CRC; the caller writes it little-endian onto the wire."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def _read_response(device_id: int, value: int) -> bytes:
    """A single-register FC03 response for ``value``."""
    body = bytes((device_id, 0x03, 0x02)) + value.to_bytes(2, "big")
    return body + _crc16(body).to_bytes(2, "little")


class LateRtuResponder:
    """Minimal RTU device on a pty that answers its first request late.

    It replies to the first FC03 with ``stale_value`` after ``delay`` seconds
    and to every later request with ``fresh_value`` immediately, mimicking a
    device whose answer outlives the gateway's hold budget.

    The serial port is opened with pyserial in a worker thread because the
    gateway holds the other end of the pair; a blocking ``read`` in the event
    loop would stall the very transport under test.
    """

    def __init__(
        self,
        port: str,
        *,
        delay: float,
        stale_value: int,
        fresh_value: int,
        device_id: int = 1,
    ) -> None:
        self._port = port
        self._delay = delay
        self._stale_value = stale_value
        self._fresh_value = fresh_value
        self._device_id = device_id
        self.addresses: list[int] = []
        self.stale_sent = False
        self._serial: serial.Serial | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        """Open the port and start answering requests."""
        self._serial = serial.Serial(self._port, baudrate=19200, timeout=0.05)
        self._thread = threading.Thread(target=self._serve, name="late-rtu", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the worker and close the port."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def _serve(self) -> None:
        assert self._serial is not None
        buffer = b""
        while not self._stop.is_set():
            try:
                buffer += self._serial.read(_REQUEST_SIZE)
            except (serial.SerialException, OSError):
                time.sleep(0.01)
                continue
            while len(buffer) >= _REQUEST_SIZE:
                frame, buffer = buffer[:_REQUEST_SIZE], buffer[_REQUEST_SIZE:]
                self.addresses.append(int.from_bytes(frame[2:4], "big"))
                first = len(self.addresses) == 1
                if first and self._stop.wait(self._delay):
                    return
                value = self._stale_value if first else self._fresh_value
                if self._write(_read_response(self._device_id, value)) and first:
                    self.stale_sent = True

    def _write(self, frame: bytes) -> bool:
        """Write a frame, retrying while the peer's pty is momentarily closed."""
        assert self._serial is not None
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not self._stop.is_set():
            try:
                self._serial.write(frame)
                return True
            except (serial.SerialException, OSError):
                time.sleep(0.01)
        return False


@pytest.mark.asyncio
async def test_late_response_never_answers_the_next_request(vsp_fixture, logger_fixture):
    """A reply that arrives after the hold budget must not be read as the next answer."""
    responder = LateRtuResponder(
        vsp_fixture.serial_ports[0],
        delay=0.6,
        stale_value=0x1111,
        fresh_value=0x2222,
    )
    responder.start()
    config = GatewayConfig(
        serial=ModbusSerialConnectionConfig(vsp_fixture.serial_ports[1], timeout=1.0),
        devices={1: GatewayDeviceConfig(device_id=1, framer="RTU")},
        bus_timeout=0.4,
        request_timeout=5.0,
    )
    gateway = ModbusGateway(config, logger=logger_fixture)
    await gateway.start()
    try:
        first = await gateway.handle_request(
            1, ReadHoldingRegistersRequest(address=0, count=1, dev_id=1)
        )
        assert isinstance(first, ExceptionResponse)
        assert first.exception_code == 0x0B

        second = await asyncio.wait_for(
            gateway.handle_request(1, ReadHoldingRegistersRequest(address=1, count=1, dev_id=1)),
            timeout=4.0,
        )

        assert isinstance(second, ReadHoldingRegistersResponse)
        # The stale payload (0x1111) would be accepted without a resync; a
        # correct gateway waits out the response window and delivers its own.
        # The payload is the detector: the wall clock alone cannot distinguish a
        # correct resync from a lucky ordering.
        assert second.registers == [0x2222]
        assert gateway._resync_deadline is None
        assert responder.addresses == [0, 1]
        assert responder.stale_sent
    finally:
        await gateway.stop()
        responder.stop()
