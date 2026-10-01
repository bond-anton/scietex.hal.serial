"""
Translator protocol for non-standard (vendor) protocols.

A `GatewayTranslator` maps standard Modbus PDUs to and from a vendor protocol.
It is the plugin contract for devices that do not speak Modbus: the gateway
decodes a standard Modbus request, hands it to the translator, sends the
resulting vendor PDU over the serial bus, then translates the vendor response
back into a standard Modbus response for the TCP client.

Both methods are pure: they perform no I/O. The gateway owns the bus.

See ``docs/design/modbus-gateway-nonstandard.md`` for the full design.

Classes:
    - GatewayTranslator: Protocol for standard Modbus <-> vendor protocol mapping.
"""

from typing import Protocol, runtime_checkable

from pymodbus.pdu import ModbusPDU


@runtime_checkable
class GatewayTranslator(Protocol):
    """
    Maps standard Modbus PDUs to and from a vendor protocol.

    Implementations are supplied by plugins via a dotted-path string in
    `GatewayDeviceConfig.translator`.
    """

    def to_vendor(self, request: ModbusPDU) -> ModbusPDU:
        """
        Translate a standard Modbus request PDU into a vendor request PDU.

        The returned PDU's `function_code` and `encode()` produce the vendor
        wire bytes. The gateway sets `dev_id` on the result before sending.

        Args:
            request (ModbusPDU): The decoded standard Modbus request.

        Returns:
            ModbusPDU: The vendor request PDU.
        """
        ...

    def to_standard(self, response: ModbusPDU) -> ModbusPDU:
        """
        Translate a vendor response PDU into a standard Modbus response PDU.

        Args:
            response (ModbusPDU): The decoded vendor response.

        Returns:
            ModbusPDU: The standard Modbus response returned to the TCP client.
        """
        ...
