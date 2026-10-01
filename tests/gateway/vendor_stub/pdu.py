"""Synthetic vendor PDU: a single-character command plus a short data payload."""

from pymodbus.datastore import ModbusServerContext
from pymodbus.pdu import ModbusPDU

# Register table the emulator answers from. Kept on the class because the
# deprecated ModbusDeviceContext API is unusable under pymodbus 3.15.
_REGISTERS: dict[int, int] = {0: 1234, 1: 5678}


class VendorRequest(ModbusPDU):
    """
    A synthetic vendor request/response PDU.

    The wire body is ``<command><data>``; the framer prepends the device id and
    appends the checksum. `function_code` is the ASCII byte of the command, so
    the generic `buildFrame` path emits the command byte correctly.

    Args:
        command (str): Single-character command (e.g. ``"R"``).
        data (bytes): Payload bytes (e.g. ``b"00"``).
    """

    function_code = 0

    def __init__(
        self, command: str = "", data: bytes = b"", dev_id: int = 1, transaction_id: int = 0
    ):
        super().__init__(dev_id=dev_id, transaction_id=transaction_id)
        self.command = command[:1]
        self.function_code = self.command.encode()[0] if self.command else 0
        self.data = data

    def encode(self) -> bytes:
        """Return the vendor body (command is carried by `function_code`)."""
        return self.data

    def decode(self, data: bytes) -> None:
        """Store the vendor body."""
        self.data = data

    async def datastore_update(self, context: ModbusServerContext, device_id: int) -> ModbusPDU:
        """
        Answer an ``"R"`` command from the emulated register table.

        Address ``N`` holds the value returned for ``"R"`` + ``f"{N:02d}"``.
        The context is unused: the deprecated `ModbusDeviceContext` API is
        unusable under pymodbus 3.15, so the table lives on the class.
        """
        _ = context, device_id
        address = int(self.data.decode())
        value = _REGISTERS.get(address, 0)
        return VendorRequest(command="R", data=f"{value:04d}".encode())
