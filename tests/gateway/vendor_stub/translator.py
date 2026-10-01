"""Synthetic translator: standard FC03 <-> vendor ``"R"`` command."""

from pymodbus.pdu import ModbusPDU
from pymodbus.pdu.register_message import (
    ReadHoldingRegistersRequest,
    ReadHoldingRegistersResponse,
)

from .pdu import VendorRequest


class VendorTranslator:
    """
    Maps standard Modbus FC03 onto the synthetic vendor ``"R"`` command.

    `to_vendor` encodes the register address as a 2-digit decimal payload;
    `to_standard` decodes the 4-digit decimal response into one register.
    """

    def to_vendor(self, request: ModbusPDU) -> ModbusPDU:
        """Standard read-holding-registers request -> vendor ``"R"`` request."""
        if not isinstance(request, ReadHoldingRegistersRequest):
            raise ValueError(f"Unsupported request: {type(request).__name__}")
        return VendorRequest(command="R", data=f"{request.address:02d}".encode())

    def to_standard(self, response: ModbusPDU) -> ModbusPDU:
        """Vendor ``"R"`` response -> standard read-holding-registers response."""
        if not isinstance(response, VendorRequest):
            raise ValueError(f"Unsupported response: {type(response).__name__}")
        value = int(response.data.decode())
        return ReadHoldingRegistersResponse(registers=[value])
