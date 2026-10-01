"""Synthetic vendor decoder: always decodes into `VendorRequest`."""

from pymodbus.pdu import DecodePDU, ModbusPDU

from .pdu import VendorRequest


class VendorDecodePDU(DecodePDU):
    """
    Decoder for the synthetic vendor protocol.

    The vendor protocol has a single PDU type, so the lookup ignores the
    function code and always returns `VendorRequest`. This mirrors how a real
    vendor decoder bypasses the standard `pdu_table`.
    """

    def __init__(self, is_server: bool = False) -> None:
        super().__init__(is_server)
        self.pdu_table = {}
        self.pdu_sub_table = {}

    def lookupPduClass(self, data: bytes) -> type[ModbusPDU] | None:
        """Always return the vendor PDU class."""
        _ = data
        return VendorRequest

    def decode(self, frame: bytes) -> ModbusPDU | None:
        """Decode ``<command><data>`` into a `VendorRequest`."""
        if not frame:
            return None
        command = frame[0:1].decode()
        pdu = VendorRequest(command=command, data=frame[1:])
        pdu.decode(frame[1:])
        return pdu
