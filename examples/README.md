# Examples

Runnable examples for `scietex.hal.serial`. Each file is a standalone script with an
`if __name__ == "__main__":` guard and can be run directly:

```bash
uv run python examples/<file>.py
```

All examples use virtual serial ports (backed by `pty`), so they run without any hardware. They
require Linux or macOS — the virtual serial layer does not work on Windows.

## Configuration

- `config.py` — builds a `SerialConnectionConfig` and a `ModbusSerialConnectionConfig`, showing
  field assignment and the `to_dict()` round trip.
- `find_serial_ports.py` — lists STM32 CDC and RS485 USB devices by VID/PID. Prints empty lists
  when no matching hardware is present.

## Virtual serial

- `virtual_serial_pair.py` — creates a `VirtualSerialPair`, a pair of connected pseudo-terminals.
- `virtual_serial_network.py` — creates two `VirtualSerialNetwork` instances bridged through a
  shared external port and forwards data between them in both directions.

## Modbus client / server

- `modbus_server.py` — starts and stops an `RS485Server` on one end of a virtual pair.
- `modbus_client.py` — runs an `RS485Client` against an `RS485Server`, reading and writing
  registers (including a float round trip).

## Gateway

- `gateway.py` — runs an `RS485Server` as the device and a `ModbusGateway` with its TCP front end
  on the other end of a virtual pair, then connects a real `pymodbus` TCP client and reads/writes
  a register through the gateway.

## Custom protocols

- `rs485_custom_request.py` — demonstrates a custom ASCII framer (device id in the first three
  bytes, LRC checksum, CRLF terminator), a custom decoder, and custom request/response PDUs
  round-tripped over a virtual pair.
