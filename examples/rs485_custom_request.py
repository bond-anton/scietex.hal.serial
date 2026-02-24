"""Custom request example.
This example is just to show how one can implement custom protocol using
`scietex.hal.serial` Server and Client abstractions and pymodbus PDU and Framer concepts.
"""

# pylint: disable=duplicate-code

import asyncio
from typing import Optional

from pymodbus import ModbusException
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ModbusPDU, DecodePDU, pdu as base
from pymodbus.framer import FramerAscii
from pymodbus.logging import Log
from pymodbus.datastore import ModbusServerContext

from scietex.hal.serial.virtual import VirtualSerialPair
from scietex.hal.serial.config import ModbusSerialConnectionConfig as Config
from scietex.hal.serial.server import RS485Server
from scietex.hal.serial.client import RS485Client
from scietex.hal.serial.utilities.checksum import lrc


class CustomizedASCIIFramer(FramerAscii):
    """Customized ASCII framer."""

    START = b""  # no starting byte.
    END = b"\r\n"
    EMPTY = b""
    MIN_SIZE = 4  # Lower payload min size to 4 bytes.

    def decode(self, data: bytes) -> tuple[int, int, int, bytes]:
        """Customized decode ADU function."""
        print("\n\nFRAMER DECODE")
        print(f"FRAMER DECODE DATA IN: {data}")
        len_used = 0
        len_data = len(data)
        while True:
            if len_data - len_used < self.MIN_SIZE:
                # Not enough payload to decode
                Log.debug("Short frame: {} wait for more payload", data, ":hex")
                break
            data_buffer = data[len_used:]
            if (data_end := data_buffer.find(self.END)) == -1:
                # END byte sequence not found.
                Log.debug("Incomplete frame: {} wait for more payload", data, ":hex")
                break
            dev_id = int(
                data_buffer[0:3].decode(encoding="utf-8"), 10
            )  # First 3 bytes for device (device_id) id
            print(f"DEVICE ID: {dev_id}")
            lrc_len = 1
            while lrc_len < len(data_buffer) - 3:
                msg = data_buffer[0 : data_end - lrc_len]
                print(lrc_len)
                print(
                    f"{lrc_len}) DATA END: {data_end}, "
                    + f"LRC: {data_buffer[data_end - lrc_len : data_end]}, {self.compute_LRC(msg)}"
                    ""
                )
                print(f"MSG: {msg}")
                try:
                    lrc_in = ord(
                        data_buffer[data_end - lrc_len : data_end].decode(
                            encoding="utf-8"
                        )
                    )
                except UnicodeDecodeError:
                    lrc_len += 1
                    continue

                if not self.check_LRC(msg, lrc_in):
                    print(f"WRONG CS FOR MSG: {msg}, LRC_IN: {lrc_in}")
                    Log.debug("LRC wrong in frame: {} skipping", data, ":hex")
                    lrc_len += 1
                    continue
                break

            len_used += data_end + 2
            msg = data_buffer[0 : data_end - lrc_len]
            lrc_in = ord(
                data_buffer[data_end - lrc_len : data_end].decode(encoding="utf-8")
            )
            print("FRAMER DECODE RAW:", data_buffer, dev_id, len_used, msg, msg[3:])
            if not self.check_LRC(msg, lrc_in):
                print(f"WRONG CS FOR MSG: {msg}, LRC_IN: {lrc_in}")
                Log.debug("LRC wrong in frame: {} skipping", data, ":hex")
                break
            return len_used, dev_id, 0, msg[3:]
        return len_used, 0, 0, self.EMPTY

    def encode(self, payload: bytes, device_id: int, _tid: int) -> bytes:
        """Customized encode ADU function."""
        print("\n\nFRAMER ENCODE")
        print(f"FRAMER DATA IN: {payload}")
        dev_id = f"{device_id:03d}".encode()  # encode device id into first 3 bytes.
        checksum = lrc(dev_id + payload)
        print(f"FRAMER Checksum: {checksum}, {chr(checksum).encode()}")
        frame = self.START + dev_id + payload + chr(checksum).encode() + self.END
        print(f"FRAMER DEV ID: {dev_id}")
        print(f"FRAMER ENCODED FRAME: {frame}")
        return frame

    def handleFrame(
        self, data: bytes, exp_devid: int, exp_tid: int
    ) -> tuple[int, ModbusPDU | None]:
        """Process new packet pattern.

        This takes in a new request packet, adds it to the current
        packet stream, and performs framing on it. That is, checks
        for complete messages, and once found, will process all that
        exist.
        """
        print(f"\n\n===Processing {data}")
        Log.debug("Processing: {}", data, ":hex")
        if not data:
            print("NO DATA")
            return 0, None
        used_len, dev_id, tid, frame_data = self.decode(data)
        print(
            f"=== LEN: {used_len}, DEV_ID: {dev_id}, TR_ID: {tid}, FRAME_DATA: {frame_data}"
        )
        print(self.decoder)
        if (res := self.decoder.decode(frame_data)) is None:
            raise ModbusIOException("Unable to decode request")
        res.dev_id = dev_id
        res.transaction_id = tid
        Log.debug("Frame advanced, resetting header!!")
        return used_len, res


class CustomizedDecodePDU(DecodePDU):
    """Customized decoder class."""

    def __init__(self, is_server: bool = False):
        super().__init__(is_server)
        self.pdu_table: dict[int, tuple[type[ModbusPDU], type[ModbusPDU]]] = {}
        self.pdu_sub_table: dict[
            int, dict[int, tuple[type[ModbusPDU], type[ModbusPDU]]]
        ] = {}

    def lookupPduClass(self, data: bytes) -> Optional[type[base.ModbusPDU]]:
        function_code = 0
        return self.pdu_table.get(function_code, (None, None))[self.pdu_inx]

    def register(self, custom_class: type[base.ModbusPDU]) -> None:
        print(f"REGISTER: {custom_class}")
        super().register(custom_class)

    def decode(self, frame: bytes) -> Optional[base.ModbusPDU]:
        print(f"DECODER DECODING FRAME: {frame}, {frame.decode()}")
        try:
            function_code = 0
            if not (
                pdu_class := self.pdu_table.get(function_code, (None, None))[
                    self.pdu_inx
                ]
            ):
                Log.debug("decode PDU failed for function code {}", function_code)
                raise ModbusException(f"Unknown response {function_code}")
            print(f"DECODER PDU TYPE: {pdu_class}")
            command: str = frame.decode()[0]
            print(f"CMD: {command}, DATA: {frame[1:]}")
            pdu = pdu_class(command=command, data=frame[1:])
            pdu.decode(frame[1:])
            Log.debug(
                "decoded PDU function_code({} sub {}) -> {} ",
                pdu.function_code,
                pdu.sub_function_code,
                str(pdu),
            )
            print(
                f"decoded PDU function_code({pdu_class.function_code}) -> {str(pdu_class)} "
            )
            pdu.registers = list(frame)[1:]
            return pdu
        except (ModbusException, ValueError, IndexError) as exc:
            Log.warning("Unable to decode frame {}", exc)
        return None


class CustomizedModbusResponse(ModbusPDU):
    """Custom modbus response."""

    function_code = 0

    def __init__(
        self,
        command: Optional[str] = None,
        data: Optional[bytes] = None,
        dev_id=1,
        transaction_id=0,
    ):
        """Initialize."""
        super().__init__(dev_id=dev_id, transaction_id=transaction_id)
        self.command: str = ""
        if command is not None:
            self.command = command[0]
        self.function_code = self.command.encode()[0]
        self.data: str = ""
        if data is not None:
            if isinstance(data, int):
                data_trunc = int(str(data)[:6])
                self.data = f"{data_trunc:<6d}".strip()
            else:
                self.data = data[:6].decode()
        self.rtu_frame_size = len(self.data)

    def encode(self):
        """Encode response pdu.

        :returns: The encoded packet message
        """
        print("RESPONSE ENCODE")
        return self.data.encode()

    def decode(self, data):
        """Decode response pdu.

        :param data: The packet payload to decode
        """
        print(f"RESPONSE DECODE {data}")
        data_str = data.decode()
        self.data = data_str


class CustomizedRequest(ModbusPDU):
    """Custom modbus request."""

    # function_code = 0
    # rtu_frame_size = 0

    def __init__(
        self,
        command: Optional[str] = None,
        data: Optional[bytes] = None,
        dev_id=1,
        transaction_id=0,
    ):
        """Initialize."""
        super().__init__(dev_id=dev_id, transaction_id=transaction_id)
        self.command: str = ""
        if command is not None:
            self.command = command[0]
        self.function_code = self.command.encode()[0]
        print(f"COMMAND: {self.command}, FUN CODE: {self.function_code}")
        self.data: str = ""
        if data is not None:
            self.data = data[:6].decode()
            # data_trunc = int(str(payload)[:6])
            # self.payload = f"{data_trunc:<6d}".strip()
        self.rtu_frame_size = len(self.data)

    def encode(self):
        """Encode."""
        # msg: str = self.command + self.payload
        msg_bytes = self.data.encode()
        # self.function_code = int.from_bytes(msg_bytes[0])
        print(f"REQUEST FUN CODE: {self.function_code}")
        print(f"REQUEST RTU Frame Size: {self.rtu_frame_size}")
        print(f"REQUEST ENCODED MSG: {msg_bytes}")
        return msg_bytes

    def decode(self, data):
        """Decode."""
        # self.rtu_frame_size = len(payload)
        print(f"REQUEST DECODE : {data}")
        data_str = data.decode()
        # self.command = data_str[0]
        self.data = data_str

    async def datastore_update(
        self, context: ModbusServerContext, device_id: int
    ) -> ModbusPDU:
        """Execute."""
        print(f"REQUEST UPD DATASTORE: {self.data}, {context}")
        _ = context
        await context.async_setValues(
            device_id=device_id, func_code=0x00, address=0, values=[0, 1, 2]
        )
        result = await context.async_getValues(
            device_id=device_id, func_code=0x00, address=0, count=3
        )
        print(f"STORE: {result}")
        response = CustomizedModbusResponse(
            self.command,
            self.data.encode(),
            dev_id=self.dev_id,
            transaction_id=self.transaction_id,
        )
        response.registers = list(result)
        return response


async def main(server_params: Config, client_params: Config):
    """Main function"""
    server = RS485Server(
        server_params,
        custom_pdu=[CustomizedRequest],
        custom_framer=CustomizedASCIIFramer,
        custom_decoder=CustomizedDecodePDU,
    )
    await server.start()

    client = RS485Client(
        client_params,
        address=1,
        custom_framer=CustomizedASCIIFramer,
        custom_decoder=CustomizedDecodePDU,
        # custom_response=[CustomizedRequest],
        custom_response=[CustomizedModbusResponse],
        label="MY DEVICE",
    )

    some_data_int = None
    request = CustomizedRequest("T", data=some_data_int, dev_id=1, transaction_id=0)

    # Send the request to the server
    response: ModbusPDU = await client.execute(request, no_response_expected=False)
    print(f"Response: {response}")
    print(f"Response: {response.registers}")
    print(f"Response: {response.data}")
    print(isinstance(response, CustomizedModbusResponse))
    print(f"SERVER CTX: {server.devices[1].store['h'].values}")
    await server.stop()


if __name__ == "__main__":
    custom_framer = CustomizedASCIIFramer(CustomizedDecodePDU(is_server=False))
    MY_DATA = b"123456"
    # MY_DATA = None
    CR = CustomizedRequest("i", data=MY_DATA, dev_id=1, transaction_id=0)
    payload_data = CR.encode()
    print(payload_data)

    # encoded_frame = custom_framer.encode(payload_data, CR.dev_id, CR.transaction_id)
    encoded_frame = custom_framer.buildFrame(CR)
    print(f"Encoded Frame: {encoded_frame}")

    # Example: Decode a custom response
    decoded_pdu = custom_framer.decode(encoded_frame)
    print(f"Decoded PDU: {decoded_pdu}")

    print("\n\nXXXXXXXXXX\n\n")

    vsp = VirtualSerialPair()
    vsp.start()
    server_config = Config(vsp.serial_ports[0])
    client_config = Config(vsp.serial_ports[1])

    asyncio.run(main(server_config, client_config))

    vsp.stop()
