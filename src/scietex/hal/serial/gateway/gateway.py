"""
Modbus gateway forwarding core.

`ModbusGateway` owns one physical serial port (the RS485 bus) and forwards
Modbus requests to devices on that bus by device id. It selects the framer,
decoder, and (optionally) translator per device from configuration.

This module contains the forwarding core only; the TCP listener lives in
`tcp_server.py`. The core is transport-agnostic: `handle_request` takes a
decoded request PDU and returns a response PDU.

Concurrency: the bus is one physical line, so all bus access is serialized by
a single `asyncio.Lock`. The framer is swapped only when the target device's
framer differs from the currently-installed one (smart swap).

See ``docs/design/modbus-gateway.md`` and
``docs/design/modbus-gateway-nonstandard.md``.
"""

import asyncio
from logging import Logger, getLogger

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException
from pymodbus.framer import FramerBase
from pymodbus.pdu import DecodePDU, ExceptionResponse, ModbusPDU
from pymodbus.transaction import TransactionManager

from .config import GatewayConfig, GatewayDeviceConfig
from .exceptions import GatewayError
from .plugin_loader import (
    build_framer,
    resolve_decoder,
    resolve_framer,
    resolve_pdu,
    resolve_translator,
)

# Modbus exception code for "gateway target device failed to respond".
_GATEWAY_TARGET_FAILED = 0x0B


class _DeviceRuntime:
    """
    Per-device runtime state: the framer/decoder pair and optional translator.

    Attributes:
        framer (FramerBase): The framer instance for this device.
        translator (GatewayTranslator | None): Translator, or None for pass-through.
    """

    __slots__ = ("framer", "translator")

    def __init__(self, framer: FramerBase, translator) -> None:
        self.framer = framer
        self.translator = translator


class ModbusGateway:
    """
    Serial<->TCP Modbus gateway forwarding core.

    Owns one serial bus and routes requests to devices by id, selecting the
    framer/decoder/translator per device from configuration.

    Args:
        config (GatewayConfig): Gateway configuration.
        logger (Logger | None): Optional logger.

    Attributes:
        config (GatewayConfig): The gateway configuration.
        logger (Logger): The logger instance.
    """

    def __init__(self, config: GatewayConfig, logger: Logger | None = None) -> None:
        self.config = config
        self.logger = logger if logger is not None else getLogger(__name__)
        self._bus: AsyncModbusSerialClient | None = None
        self._lock = asyncio.Lock()
        self._current_framer: FramerBase | None = None
        self._devices: dict[int, _DeviceRuntime] = {}
        self._default_runtime: _DeviceRuntime | None = None

    # -- lifecycle ---------------------------------------------------------

    async def start(self) -> None:
        """
        Open the serial bus and build per-device runtime state.

        Idempotent: a second call while running has no effect.

        A failed initial connect does not abort startup: the async client
        reconnects on the next request, so the gateway stays up and recovers
        once the port is available. The failure is logged as a warning so a
        dead bus is not reported as a healthy start.
        """
        if self._bus is not None:
            return
        self._build_runtimes()
        self._bus = self._create_bus()
        if await self._bus.connect():
            self.logger.info("Gateway bus opened on %s", self.config.serial.port)
        else:
            self.logger.warning(
                "Gateway bus could not be opened on %s; will retry on the next request",
                self.config.serial.port,
            )

    async def stop(self) -> None:
        """Close the serial bus. Idempotent."""
        if self._bus is None:
            return
        self._bus.close()
        self._bus = None
        self._current_framer = None
        self.logger.info("Gateway bus closed")

    # -- construction helpers ---------------------------------------------

    def _create_bus(self) -> AsyncModbusSerialClient:
        """Create the serial client with a placeholder framer (swapped per request)."""
        serial = self.config.serial
        client = AsyncModbusSerialClient(
            port=serial.port,
            baudrate=serial.baudrate,
            bytesize=serial.bytesize,
            parity=serial.parity,
            # pymodbus types stopbits as int; the config model allows 1.5 (float),
            # which pyserial accepts at runtime.
            stopbits=serial.stopbits,  # ty: ignore[invalid-argument-type]
            timeout=serial.timeout if serial.timeout is not None else 3,
            retries=self.config.bus_retries,
            name="gateway",
        )
        # Install a default framer so the client is usable before the first swap.
        default_framer = self._build_framer_for(self.config.default_framer, None, [])
        client.ctx = TransactionManager(
            client.comm_params,
            default_framer,
            retries=self.config.bus_retries,
            is_server=False,
            trace_packet=None,
            trace_pdu=None,
            trace_connect=None,
        )
        self._current_framer = default_framer
        return client

    def _build_framer_for(
        self, framer_ref: str, decoder_ref: str | None, pdus: list[str]
    ) -> FramerBase:
        """Build a framer instance with its decoder and registered PDUs."""
        if decoder_ref is not None:
            decoder = resolve_decoder(decoder_ref)(False)
        else:
            decoder = DecodePDU(False)
        for pdu_ref in pdus:
            decoder.register(resolve_pdu(pdu_ref))
        framer_cls = resolve_framer(framer_ref)
        return build_framer(framer_cls, decoder)

    def _build_runtimes(self) -> None:
        """Build the per-device runtime table and the default runtime."""
        self._devices = {}
        for device_id, device in self.config.devices.items():
            self._devices[device_id] = self._build_device_runtime(device)
        self._default_runtime = _DeviceRuntime(
            framer=self._build_framer_for(self.config.default_framer, None, []),
            translator=None,
        )

    def _build_device_runtime(self, device: GatewayDeviceConfig) -> _DeviceRuntime:
        """Build runtime state for one configured device."""
        framer = self._build_framer_for(device.framer, device.decoder, device.pdus)
        translator = None
        if device.translator is not None:
            translator = resolve_translator(device.translator)()
        return _DeviceRuntime(framer=framer, translator=translator)

    def _runtime_for(self, device_id: int) -> _DeviceRuntime:
        """
        Return the runtime for a device id.

        Raises:
            GatewayError: If the device is unknown and unknown devices are not allowed.
        """
        runtime = self._devices.get(device_id)
        if runtime is not None:
            return runtime
        if self.config.allow_unknown_devices and self._default_runtime is not None:
            return self._default_runtime
        raise GatewayError(f"Unknown device id: {device_id}")

    # -- request handling --------------------------------------------------

    async def handle_request(self, device_id: int, request: ModbusPDU) -> ModbusPDU:
        """
        Forward a decoded request to the bus and return a response PDU.

        This is the transport-agnostic entry point used by the TCP server. It
        never raises for bus/device failures: those are mapped to a Modbus
        exception response (0x0B) so the TCP connection stays open.

        Args:
            device_id (int): Target device id.
            request (ModbusPDU): The decoded request PDU.

        Returns:
            ModbusPDU: The response PDU (a normal response or an exception response).
        """
        try:
            runtime = self._runtime_for(device_id)
        except GatewayError as exc:
            self.logger.warning("%s", exc)
            return ExceptionResponse(request.function_code, _GATEWAY_TARGET_FAILED)

        try:
            return await self._forward(device_id, request, runtime)
        except (ModbusException, GatewayError, asyncio.TimeoutError) as exc:
            self.logger.error("Bus failure for device %s: %s", device_id, exc)
            return ExceptionResponse(request.function_code, _GATEWAY_TARGET_FAILED)

    async def _forward(
        self, device_id: int, request: ModbusPDU, runtime: _DeviceRuntime
    ) -> ModbusPDU:
        """Translate, swap framer, execute, and translate back."""
        if self._bus is None:
            raise GatewayError("Gateway bus is not started")

        vendor_request = request
        if runtime.translator is not None:
            vendor_request = runtime.translator.to_vendor(request)
        vendor_request.dev_id = device_id

        async with self._lock:
            if self._current_framer is not runtime.framer:
                self._bus.ctx.framer = runtime.framer
                self._current_framer = runtime.framer
            vendor_response = await self._bus.execute(False, vendor_request)

        if runtime.translator is not None:
            return runtime.translator.to_standard(vendor_response)
        return vendor_response
