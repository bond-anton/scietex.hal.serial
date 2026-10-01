"""Synthetic vendor ASCII framer: ``<3-digit dev_id><body><checksum>\\r``."""

from pymodbus.framer import FramerAscii
from pymodbus.pdu import ModbusPDU


def _checksum(data: bytes) -> int:
    """Simple XOR checksum over the frame body."""
    result = 0
    for byte in data:
        result ^= byte
    return result


class VendorFramer(FramerAscii):
    """ASCII framer for the synthetic vendor protocol."""

    START = b""
    END = b"\r"
    EMPTY = b""
    MIN_SIZE = 6

    def decode(self, data: bytes) -> tuple[int, int, int, bytes]:
        """Decode one frame into (used, dev_id, tid, body)."""
        len_used = 0
        len_data = len(data)
        while True:
            if len_data - len_used < self.MIN_SIZE:
                break
            buffer = data[len_used:]
            end = buffer.find(self.END)
            if end == -1:
                break
            dev_id = int(buffer[0:3], 10)
            checksum = buffer[end - 1]
            body = buffer[0 : end - 1]
            len_used += end + 1
            if _checksum(body) != checksum:
                break
            return len_used, dev_id, 0, body[3:]
        return len_used, 0, 0, self.EMPTY

    def encode(self, payload: bytes, device_id: int, _tid: int) -> bytes:
        """Encode a body into a vendor frame."""
        dev_id = f"{device_id:03d}".encode()
        body = dev_id + payload
        return self.START + body + bytes([_checksum(body)]) + self.END

    def handleFrame(
        self, data: bytes, exp_devid: int, exp_tid: int
    ) -> tuple[int, ModbusPDU | None]:
        """Decode a frame and hand the body to the registered decoder."""
        if not data:
            return 0, None
        used_len, dev_id, tid, body = self.decode(data)
        if not body:
            return used_len, None
        result = self.decoder.decode(body)
        if result is None:
            return used_len, None
        result.dev_id = dev_id
        result.transaction_id = tid
        return used_len, result
