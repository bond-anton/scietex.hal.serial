"""Custom request test."""

import logging
from typing import Optional, Union

import pytest

from pymodbus import ModbusException
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ModbusPDU, DecodePDU, pdu as base
from pymodbus.framer import FramerAscii
from pymodbus.logging import Log
from pymodbus.datastore import ModbusSlaveContext

try:
    from src.scietex.hal.serial.config import ModbusSerialConnectionConfig as Config
    from src.scietex.hal.serial.server import RS485Server
    from src.scietex.hal.serial.client import RS485Client
except ModuleNotFoundError:
    from scietex.hal.serial.config import ModbusSerialConnectionConfig as Config
    from scietex.hal.serial.server import RS485Server
    from scietex.hal.serial.client import RS485Client


# pylint: disable=import-error,unused-import
from tests.fixtures import (
    logger_fixture,
    vsp_fixture,
    store_fixture,
    single_slave_fixture,
    server_config,
    client_config,
    rs485_srv,
)


Log.setLevel(logging.DEBUG)


class CustomASCIIFramer(FramerAscii):
    """Custom ASCII framer without start byte."""

    START = b""
    MIN_SIZE = 4

    def decode(self, data: bytes) -> tuple[int, int, int, bytes]:
        """Decode ADU."""
        used_len = 0
        data_len = len(data)
        while True:
            if data_len - used_len < self.MIN_SIZE:
                Log.debug("Short frame: {} wait for more data", data, ":hex")
                return used_len, 0, 0, self.EMPTY
            buffer = data[used_len:]
            if (end := buffer.find(self.END)) == -1:
                Log.debug("Incomplete frame: {} wait for more data", data, ":hex")
                return used_len, 0, 0, self.EMPTY
            dev_id = int(buffer[0:3], 10)
            lrc = int(buffer[end - 2 : end], 16)
            msg = buffer[0 : end - 2]
            used_len += end + 2
            if not self.check_LRC(msg[0:], lrc):
                Log.debug("LRC wrong in frame: {} skipping", data, ":hex")
                continue
            return used_len, dev_id, 0, msg[3:]

    def encode(self, data: bytes, device_id: int, _tid: int) -> bytes:
        """Encode ADU."""
        dev_id = f"{device_id:03d}".encode()
        checksum = self.compute_LRC(dev_id + data)
        frame = self.START + dev_id + data + f"{checksum:02x}".encode() + self.END
        return frame

    def _processIncomingFrame(self, data: bytes) -> tuple[int, Union[ModbusPDU, None]]:
        """Process new packet pattern.

        This takes in a new request packet, adds it to the current
        packet stream, and performs framing on it. That is, checks
        for complete messages, and once found, will process all that
        exist.
        """
        Log.debug("Processing: {}", data, ":hex")
        if not data:
            return 0, None
        used_len, dev_id, tid, frame_data = self.decode(data)
        if not frame_data:
            return used_len, None
        if (result := self.decoder.decode(frame_data)) is None:
            raise ModbusIOException("Unable to decode request")
        result.dev_id = dev_id
        result.transaction_id = tid
        Log.debug("Frame advanced, resetting header!!")
        return used_len, result


class CustomDecodePDU(DecodePDU):
    """Custom decoder."""

    def __init__(self, is_server: bool = False):
        super().__init__(is_server)
        self.lookup: dict[int, type[base.ModbusPDU]] = {}
        self.sub_lookup: dict[int, dict[int, type[base.ModbusPDU]]] = {}

    def lookupPduClass(self, data: bytes) -> Optional[type[base.ModbusPDU]]:
        function_code = 0
        return self.lookup.get(function_code, None)

    def decode(self, frame: bytes) -> Optional[base.ModbusPDU]:
        try:
            function_code = 0
            if not (pdu_type := self.lookup.get(function_code, None)):
                Log.debug("decode PDU failed for function code {}", function_code)
                raise ModbusException(f"Unknown response {function_code}")
            command: str = frame.decode()[0]
            pdu = pdu_type(command=command, data=int(frame.decode()[1:]))
            pdu.decode(frame[1:])
            Log.debug(
                "decoded PDU function_code({} sub {}) -> {} ",
                pdu.function_code,
                pdu.sub_function_code,
                str(pdu),
            )
            return pdu
        except (ModbusException, ValueError, IndexError) as exc:
            Log.warning("Unable to decode frame {}", exc)
        return None


class CustomModbusResponse(ModbusPDU):
    """Custom modbus response."""

    function_code = 0

    def __init__(
        self,
        command: Optional[str] = None,
        data: Optional[bytes] = None,
        slave=1,
        transaction=0,
    ):
        """Initialize."""
        super().__init__(dev_id=slave, transaction_id=transaction)
        self.command: str = ""
        if command is not None:
            self.command = command[0]
        self.function_code = self.command.encode()[0]
        self.data: str = ""
        if data is not None:
            if isinstance(data, int):
                data_truncated = int(str(data)[:6])
                self.data = f"{data_truncated:<6d}".strip()
            else:
                self.data = data.decode()
        self.rtu_frame_size = len(self.data)

    def encode(self):
        """Encode response pdu.

        :returns: The encoded packet message
        """
        return self.data.encode()

    def decode(self, data):
        """Decode response pdu.

        :param data: The packet data to decode
        """
        data_str = data.decode()
        self.data = data_str


class CustomRequest(ModbusPDU):
    """Custom modbus request."""

    function_code = 0
    # rtu_frame_size = 0

    def __init__(
        self,
        command: Optional[str] = None,
        data: Optional[int] = None,
        slave=1,
        transaction=0,
    ):
        """Initialize."""
        super().__init__(dev_id=slave, transaction_id=transaction)
        self.command: str = ""
        if command is not None:
            self.command = command[0]
        self.function_code = self.command.encode()[0]
        self.data: str = ""
        if data is not None:
            data_truncated = int(str(data)[:6])
            self.data = f"{data_truncated:<6d}".strip()
        self.rtu_frame_size = len(self.data)

    def encode(self):
        """Encode."""
        msg_bytes = self.data.encode()
        return msg_bytes

    def decode(self, data):
        """Decode."""
        data_str = data.decode()
        self.data = data_str

    async def update_datastore(self, context: ModbusSlaveContext) -> ModbusPDU:
        """Execute."""
        _ = context
        return CustomModbusResponse(
            self.command,
            self.data.encode(),
            slave=self.dev_id,
            transaction=self.transaction_id,
        )


def test_custom_framer():
    """Test custom framer operation."""
    custom_framer = CustomASCIIFramer(CustomDecodePDU(is_server=False))
    my_data = 123456
    # my_data = None
    cr = CustomRequest("i", data=my_data, slave=1, transaction=0)
    payload = cr.encode()
    assert payload == b"123456"

    encoded_frame = custom_framer.buildFrame(cr)
    assert encoded_frame == b"001i123456d1\r\n"

    # Example: Decode a custom response
    decoded_pdu = custom_framer.decode(encoded_frame)
    assert decoded_pdu == (14, 1, 0, b"i123456")


@pytest.mark.asyncio
# pylint: disable=redefined-outer-name
async def test_custom_request_client(vsp_fixture):
    """Test client and server with custom framer and request."""
    server_config = Config(vsp_fixture.serial_ports[0])
    client_config = Config(vsp_fixture.serial_ports[1])

    server = RS485Server(
        server_config,
        custom_pdu=[CustomRequest],
        custom_framer=CustomASCIIFramer,
        custom_decoder=CustomDecodePDU,
    )
    await server.start()
    client = RS485Client(
        client_config,
        address=1,
        custom_framer=CustomASCIIFramer,
        custom_decoder=CustomDecodePDU,
        custom_response=[CustomModbusResponse],
        label="MY TOY",
    )
    some_data = 123456
    request = CustomRequest("i", data=some_data, slave=1, transaction=0)
    # Send the request to the server
    response = await client.execute(request, no_response_expected=False)
    assert isinstance(response, CustomModbusResponse)
    assert response.data == f"{some_data}"

    await server.stop()


if __name__ == "__main__":
    pytest.main()
