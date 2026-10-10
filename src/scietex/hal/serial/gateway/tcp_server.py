"""
Gateway TCP server.

`GatewayTcpServer` accepts standard Modbus/TCP clients, decodes their requests
with `FramerSocket`, forwards them to the `ModbusGateway` core, and encodes the
responses back. It is a custom asyncio server: pymodbus's `ModbusTcpServer`
answers from a datastore and has no forwarding hook.

Each connection gets its own `FramerSocket` and `DecodePDU` (no state bleed).
The client's transaction id is captured server-side and echoed in the response,
because the serial-side `TransactionManager` overwrites the request TID.

See ``docs/design/modbus-gateway.md``.
"""

import asyncio
from logging import Logger, getLogger

from pymodbus.framer import FramerSocket
from pymodbus.pdu import DecodePDU, ModbusPDU

from .config import GatewayConfig
from .gateway import ModbusGateway
from .plugin_loader import resolve_pdu

# Maximum bytes buffered per connection before the connection is dropped.
# Guards against a client that never sends a complete frame.
_MAX_BUFFER = 64 * 1024

# Read chunk size.
_READ_SIZE = 4096


class GatewayTcpServer:
    """
    Asyncio Modbus/TCP front end for a `ModbusGateway`.

    Args:
        config (GatewayConfig): Gateway configuration (host/port and devices).
        gateway (ModbusGateway): The forwarding core.
        logger (Logger | None): Optional logger.

    Attributes:
        config (GatewayConfig): The gateway configuration.
        gateway (ModbusGateway): The forwarding core.
        logger (Logger): The logger instance.
    """

    def __init__(
        self,
        config: GatewayConfig,
        gateway: ModbusGateway,
        logger: Logger | None = None,
    ) -> None:
        self.config = config
        self.gateway = gateway
        self.logger = logger if logger is not None else getLogger(__name__)
        self._server: asyncio.AbstractServer | None = None
        self._client_count = 0
        self._request_pdus: list[type[ModbusPDU]] = self._collect_request_pdus()

    # -- telemetry ---------------------------------------------------------

    @property
    def client_count(self) -> int:
        """Number of currently connected TCP clients."""
        return self._client_count

    @property
    def tcp_listening(self) -> bool:
        """Whether the TCP listener is currently bound."""
        return self._server is not None

    @property
    def tcp_host(self) -> str:
        """The configured TCP bind address."""
        return self.config.host

    @property
    def tcp_port(self) -> int:
        """The configured TCP bind port."""
        return self.config.port

    def _collect_request_pdus(self) -> list[type[ModbusPDU]]:
        """Union of custom request PDU classes declared across all devices."""
        pdus: list[type[ModbusPDU]] = []
        seen: set[str] = set()
        for device in self.config.devices.values():
            for pdu_ref in device.pdus:
                if pdu_ref not in seen:
                    seen.add(pdu_ref)
                    pdus.append(resolve_pdu(pdu_ref))
        return pdus

    async def start(self) -> None:
        """Start listening. Idempotent."""
        if self._server is not None:
            return
        self._server = await asyncio.start_server(
            self._handle_connection,
            host=self.config.host,
            port=self.config.port,
        )
        self.logger.info(
            "Gateway TCP server listening on %s:%s", self.config.host, self.config.port
        )

    async def stop(self) -> None:
        """Stop listening. Idempotent."""
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None
        self.logger.info("Gateway TCP server stopped")

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Serve one TCP client connection."""
        decoder = DecodePDU(True)
        for pdu_cls in self._request_pdus:
            decoder.register(pdu_cls)
        framer = FramerSocket(decoder)
        buffer = b""
        self._client_count += 1
        try:
            while chunk := await reader.read(_READ_SIZE):
                buffer += chunk
                if len(buffer) > _MAX_BUFFER:
                    self.logger.warning("TCP buffer overflow; closing connection")
                    break
                buffer = await self._drain_buffer(buffer, framer, writer)
        except (ConnectionError, asyncio.IncompleteReadError):
            self.logger.debug("TCP client disconnected")
        finally:
            self._client_count -= 1
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                # The peer may already be gone; nothing to clean up.
                pass

    async def _drain_buffer(
        self, buffer: bytes, framer: FramerSocket, writer: asyncio.StreamWriter
    ) -> bytes:
        """Decode and dispatch every complete frame in the buffer."""
        while buffer:
            used, dev_id, tid, pdu_bytes = framer.decode(buffer)
            if used == 0:
                # Incomplete frame: wait for more bytes.
                break
            buffer = buffer[used:]
            await self._dispatch(writer, dev_id, tid, pdu_bytes, framer)
        return buffer

    async def _dispatch(
        self,
        writer: asyncio.StreamWriter,
        dev_id: int,
        tid: int,
        pdu_bytes: bytes,
        framer: FramerSocket,
    ) -> None:
        """Decode a request PDU, forward it, and write the encoded response."""
        request = framer.decoder.decode(pdu_bytes)
        if request is None:
            self.logger.warning("Undecodable request from device %s", dev_id)
            return
        request.dev_id = dev_id
        request.transaction_id = tid
        response = await self.gateway.handle_request(dev_id, request)
        payload = response.function_code.to_bytes(1, "big") + response.encode()
        frame = framer.encode(payload, dev_id, tid)
        writer.write(frame)
        await writer.drain()
