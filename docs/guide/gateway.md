# Modbus Gateway

`ModbusGateway` bridges a serial RS485 bus to TCP/IP. It owns one serial port,
accepts standard Modbus/TCP clients, and routes each request to the right device
on the bus **by device id**. Clients need no special protocol — they speak plain
Modbus/TCP.

## When to use it

Use the gateway when several TCP clients must share one physical RS485 bus, or
when a TCP-only application needs to reach serial Modbus devices. The gateway is
a **frame-level proxy**: it forwards to the bus and does not answer from a
datastore.

## Basic setup

```python
import asyncio

from scietex.hal.serial import (
    GatewayConfig,
    GatewayDeviceConfig,
    ModbusGateway,
    ModbusSerialConnectionConfig,
)


async def main():
    config = GatewayConfig(
        serial=ModbusSerialConnectionConfig("/dev/ttyUSB0", baudrate=9600),
        host="0.0.0.0",
        port=502,
        default_framer="RTU",
        devices={
            1: GatewayDeviceConfig(device_id=1, framer="RTU"),
            2: GatewayDeviceConfig(device_id=2, framer="ASCII"),
        },
    )

    gateway = ModbusGateway(config)
    await gateway.start()

    # ... serve until shutdown ...

    await gateway.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

A TCP client then connects to `host:port` and issues normal Modbus/TCP requests
with the target device id as the unit id.

## Configuration

`GatewayConfig` fields:

| Field | Meaning |
| --- | --- |
| `serial` | The serial bus connection (`ModbusSerialConnectionConfig`). |
| `host` / `port` | TCP bind address and port (default `0.0.0.0:502`). |
| `default_framer` | Framer for devices without an explicit entry (`"RTU"` or `"ASCII"`). |
| `devices` | Per-device routing table, keyed by device id. |
| `allow_unknown_devices` | If `True`, unknown ids use the default framer; if `False` (default), they are rejected. |
| `bus_retries` | Retry count for bus transactions. |

`GatewayDeviceConfig` fields:

| Field | Meaning |
| --- | --- |
| `device_id` | Modbus device id (1..247). |
| `framer` | `"RTU"`, `"ASCII"`, or a dotted path to a custom framer. |
| `decoder` | Dotted path to a custom decoder, or `None`. |
| `pdus` | Dotted paths to custom PDU classes to register. |
| `translator` | Dotted path to a `GatewayTranslator`, or `None` for pass-through. |

All plugin references are resolved at construction time, so a bad dotted path
fails fast with `GatewayConfigError` rather than at the first request.

## Framer selection

The gateway keeps one framer per device and swaps the serial framer only when
the target device needs a different one. An all-RTU bus performs **zero swaps
after the first request**. Swaps happen under an `asyncio.Lock`, because the bus
is a single physical line.

## Non-Modbus (vendor) devices

Some devices speak a vendor protocol rather than Modbus. For those, supply a
`translator` — a plugin implementing the `GatewayTranslator` protocol:

```python
class GatewayTranslator(Protocol):
    def to_vendor(self, request: ModbusPDU) -> ModbusPDU: ...
    def to_standard(self, response: ModbusPDU) -> ModbusPDU: ...
```

The gateway translates the standard request into a vendor command, sends it over
the bus, and translates the vendor response back into a standard Modbus
response. The TCP client never knows the device is non-Modbus. See the
[non-standard protocol design](../design/modbus-gateway-nonstandard.md) for the
full contract.

## Error handling

A bus or device failure is returned to the TCP client as a Modbus exception
response (code `0x0B`, gateway target failed to respond). The TCP connection
stays open, so the client can retry. `handle_request` never raises.

## See also

- [Gateway API reference](../api/gateway.md)
- [Gateway design document](../design/modbus-gateway.md)
- [Non-standard protocol design](../design/modbus-gateway-nonstandard.md)
