"""Custom request example.

Demonstrates a custom protocol over the `scietex.hal.serial` Server and Client abstractions using
pymodbus PDU and Framer concepts: a custom ASCII framer (device id encoded in the first three
bytes, LRC checksum, CRLF terminator), a custom decoder, and custom request/response PDUs
round-tripped over a virtual serial pair.
"""

import asyncio

from pymodbus import ModbusException
from pymodbus.constants import ExcCodes
from pymodbus.datastore import ModbusServerContext
from pymodbus.exceptions import ModbusIOException
from pymodbus.framer import FramerAscii
from pymodbus.logging import Log
from pymodbus.pdu import DecodePDU, ModbusPDU
from pymodbus.pdu import pdu as base

from scietex.hal.serial.client import RS485Client
from scietex.hal.serial.config import ModbusSerialConnectionConfig
from scietex.hal.serial.server import RS485Server
from scietex.hal.serial.utilities.checksum import lrc
from scietex.hal.serial.virtual import VirtualSerialPair


class CustomizedASCIIFramer(FramerAscii):
    """ASCII framer that encodes the device id in the first three bytes."""

    START = b""
    END = b"\r\n"
    EMPTY = b""
    MIN_SIZE = 4

    def decode(self, data: bytes) -> tuple[int, int, int, bytes]:
        """Decode one ADU, returning (bytes_used, device_id, transaction_id, payload)."""
        len_used = 0
        len_data = len(data)
        while True:
            if len_data - len_used < self.MIN_SIZE:
                Log.debug("Short frame: {} wait for more payload", data, ":hex")
                break
            data_buffer = data[len_used:]
            if (data_end := data_buffer.find(self.END)) == -1:
                Log.debug("Incomplete frame: {} wait for more payload", data, ":hex")
                break
            dev_id = int(data_buffer[0:3].decode(encoding="utf-8"), 10)
            lrc_len = 1
            while lrc_len < len(data_buffer) - 3:
                msg = data_buffer[0 : data_end - lrc_len]
                try:
                    lrc_in = ord(
                        data_buffer[data_end - lrc_len : data_end].decode(encoding="utf-8")
                    )
                except UnicodeDecodeError:
                    lrc_len += 1
                    continue
                if not self.check_LRC(msg, lrc_in):
                    Log.debug("LRC wrong in frame: {} skipping", data, ":hex")
                    lrc_len += 1
                    continue
                break
            len_used += data_end + 2
            msg = data_buffer[0 : data_end - lrc_len]
            lrc_in = ord(data_buffer[data_end - lrc_len : data_end].decode(encoding="utf-8"))
            if not self.check_LRC(msg, lrc_in):
                Log.debug("LRC wrong in frame: {} skipping", data, ":hex")
                break
            return len_used, dev_id, 0, msg[3:]
        return len_used, 0, 0, self.EMPTY

    def encode(self, payload: bytes, device_id: int, _tid: int) -> bytes:
        """Encode an ADU: three-byte device id, payload, LRC, and CRLF terminator."""
        dev_id = f"{device_id:03d}".encode()
        checksum = lrc(dev_id + payload)
        return self.START + dev_id + payload + chr(checksum).encode() + self.END

    def handleFrame(
        self, data: bytes, exp_devid: int, exp_tid: int
    ) -> tuple[int, ModbusPDU | None]:
        """Frame and decode one request, returning (bytes_used, pdu)."""
        Log.debug("Processing: {}", data, ":hex")
        if not data:
            return 0, None
        used_len, dev_id, tid, frame_data = self.decode(data)
        if (res := self.decoder.decode(frame_data)) is None:
            raise ModbusIOException("Unable to decode request")
        res.dev_id = dev_id
        res.transaction_id = tid
        return used_len, res


class CustomizedDecodePDU(DecodePDU):
    """Decoder that maps function code 0 to the custom request/response PDUs."""

    def __init__(self, is_server: bool = False):
        super().__init__(is_server)
        self.pdu_table: dict[int, tuple[type[ModbusPDU], type[ModbusPDU]]] = {}
        self.pdu_sub_table: dict[int, dict[int, tuple[type[ModbusPDU], type[ModbusPDU]]]] = {}

    def decode(self, frame: bytes) -> base.ModbusPDU | None:
        """Decode the payload into a custom PDU (first byte is the command)."""
        try:
            function_code = 0
            if not (pdu_class := self.pdu_table.get(function_code, (None, None))[self.pdu_inx]):
                raise ModbusException(f"Unknown response {function_code}")
            command: str = frame.decode()[0]
            if not issubclass(pdu_class, (CustomizedRequest, CustomizedModbusResponse)):
                raise ModbusException(f"Unknown response PDU {type(pdu_class)}")
            pdu = pdu_class(command=command, data=frame[1:])
            pdu.decode(frame[1:])
            return pdu
        except (ModbusException, ValueError, IndexError) as exc:
            Log.warning("Unable to decode frame {}", exc)
        return None


class CustomizedModbusResponse(ModbusPDU):
    """Custom response: echoes the command and carries up to six bytes of data."""

    function_code = 0

    def __init__(
        self,
        command: str | None = None,
        data: bytes | None = None,
        dev_id: int = 1,
        transaction_id: int = 0,
    ):
        super().__init__(dev_id=dev_id, transaction_id=transaction_id)
        self.command: str = ""
        if command is not None:
            self.command = command[0]
        self.function_code = self.command.encode()[0]
        self.data: str = ""
        if data is not None:
            self.data = data[:6].decode()
        self.rtu_frame_size = len(self.data)

    def encode(self) -> bytes:
        """Encode the response payload."""
        return self.data.encode()

    def decode(self, data: bytes) -> None:
        """Decode the response payload."""
        self.data = data.decode()


class CustomizedRequest(ModbusPDU):
    """Custom request: a command byte plus up to six bytes of data."""

    def __init__(
        self,
        command: str | None = None,
        data: bytes | None = None,
        dev_id: int = 1,
        transaction_id: int = 0,
    ):
        super().__init__(dev_id=dev_id, transaction_id=transaction_id)
        self.command: str = ""
        if command is not None:
            self.command = command[0]
        self.function_code = self.command.encode()[0]
        self.data: str = ""
        if data is not None:
            self.data = data[:6].decode()
        self.rtu_frame_size = len(self.data)

    def encode(self) -> bytes:
        """Encode the request payload."""
        return self.data.encode()

    def decode(self, data: bytes) -> None:
        """Decode the request payload."""
        self.data = data.decode()

    async def datastore_update(self, context: ModbusServerContext, device_id: int) -> ModbusPDU:
        """Write holding registers, read them back, and respond."""
        response = CustomizedModbusResponse(
            self.command,
            self.data.encode(),
            dev_id=self.dev_id,
            transaction_id=self.transaction_id,
        )
        await context.async_setValues(
            device_id=device_id, func_code=0x06, address=0, values=[0, 1, 2]
        )
        result = await context.async_getValues(
            device_id=device_id, func_code=0x03, address=0, count=3
        )
        if not isinstance(result, ExcCodes):
            response.registers = list(result)
        return response


async def main() -> None:
    """Run a custom request/response round trip over a virtual serial pair."""
    vsp = VirtualSerialPair()
    vsp.start()

    server = RS485Server(
        ModbusSerialConnectionConfig(vsp.serial_ports[0]),
        custom_pdu=[CustomizedRequest],
        custom_framer=CustomizedASCIIFramer,
        custom_decoder=CustomizedDecodePDU,
    )
    await server.start()

    client = RS485Client(
        ModbusSerialConnectionConfig(vsp.serial_ports[1]),
        address=1,
        custom_framer=CustomizedASCIIFramer,
        custom_decoder=CustomizedDecodePDU,
        custom_response=[CustomizedModbusResponse],
        label="Custom device",
    )

    request = CustomizedRequest("T", data=b"123456", dev_id=1, transaction_id=0)
    print(f"Sending request: command={request.command!r}, data={request.data!r}")

    response = await client.execute(request, no_response_expected=False)
    if isinstance(response, CustomizedModbusResponse):
        print(f"Received response: command={response.command!r}, data={response.data!r}")
    else:
        print(f"Received unexpected response: {response}")

    # The request wrote [0, 1, 2] to the holding registers; confirm on the live server context.
    assert server.server is not None
    holding = await server.server.context.async_getValues(1, 0x03, 0, 3)
    print(f"Device 1 holding registers: {holding}")

    await server.stop()
    vsp.stop()


if __name__ == "__main__":
    asyncio.run(main())
