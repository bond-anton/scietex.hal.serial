# API Reference

The public API is re-exported from the top-level package, so most users only need:

```python
from scietex.hal.serial import RS485Client, RS485Server, ModbusGateway
```

The pages below document each module in full. Everything listed here is part of
the stable public surface unless marked otherwise.

| Module | Contents |
| --- | --- |
| [Configuration](config.md) | Connection config dataclasses and validation. |
| [Virtual](virtual.md) | `VirtualSerialPair`, `VirtualSerialNetwork`. |
| [Server](server.md) | `RS485Server`, `ReactiveSequentialDataBlock`. |
| [Client](client.md) | `RS485Client`. |
| [Gateway](gateway.md) | `ModbusGateway`, `GatewayTcpServer`, config, plugin loader, translator protocol. |
| [Utilities](utilities.md) | Checksums, numeric helpers, Modbus helpers, port discovery. |
