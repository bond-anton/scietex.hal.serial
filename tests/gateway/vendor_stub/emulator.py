"""Synthetic vendor device emulator for the serial side of the gateway."""

from logging import Logger

from pymodbus.datastore import ModbusDeviceContext, ModbusSequentialDataBlock

from scietex.hal.serial.config import ModbusSerialConnectionConfig
from scietex.hal.serial.server import RS485Server

from .decoder import VendorDecodePDU
from .framer import VendorFramer
from .pdu import VendorRequest


class VendorEmulator(RS485Server):
    """
    Emulates a synthetic vendor device.

    Answers the ``"R"`` command with a 4-digit decimal value read from a
    register table, so the gateway's translator can be verified end-to-end.

    Args:
        con_params (ModbusSerialConnectionConfig): Serial connection config.
        values (dict[int, int]): Register address -> value map.
        address (int): Device id.
        logger (Logger | None): Optional logger.
    """

    def __init__(
        self,
        con_params: ModbusSerialConnectionConfig,
        address: int = 1,
        logger: Logger | None = None,
    ) -> None:
        block = ModbusSequentialDataBlock(0x01, [0] * 16)
        store = ModbusDeviceContext(hr=block)
        super().__init__(
            con_params,
            devices={address: store},
            custom_pdu=[VendorRequest],
            custom_framer=VendorFramer,
            custom_decoder=VendorDecodePDU,
            logger=logger,
        )
