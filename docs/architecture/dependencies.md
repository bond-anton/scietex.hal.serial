# Dependencies

Architectural dependency relationships (intra-package edges plus the significant
third-party boundaries). Third-party packages are listed only where they define
a boundary.

## Intra-package dependency graph

Verified from imports in `src/scietex/hal/serial/`.

```
version.py ──────────────┐
                         ▼
config/ ─────────────► utilities/modbus.py ─────► client/rs485_client.py
   ▲                         ▲                          │
   │                         │                          ▼
   │                    server/rs485_server.py    utilities/numeric.py
   │                         │
   │                         ▼
   │                    server/modbus_datablock.py
   │
   ├──────────────► virtual/virtual_serial_network.py ──► virtual/worker.py
   │                          ▲
   └──────────────► virtual/virtual_serial_pair.py
```

Edges (source → target):

| Source | Target | Symbols |
| --- | --- | --- |
| `client/rs485_client.py` | `config` | `SerialConnectionConfigModel`, `ModbusSerialConnectionConfigModel` |
| `client/rs485_client.py` | `utilities.modbus` | `modbus_get_client`, `modbus_execute`, `modbus_read_registers`, `modbus_write_registers`, `modbus_write_register` |
| `client/rs485_client.py` | `utilities.numeric` | `ByteOrder`, signed/float/32-bit helpers |
| `server/rs485_server.py` | `config` | config models |
| `server/rs485_server.py` | `utilities.modbus` | `modbus_connection_config` |
| `server/rs485_server.py` | `version` | `__version__` |
| `server/rs485_server.py` | `server.modbus_datablock` | `ReactiveSequentialDataBlock` |
| `utilities/modbus.py` | `config` | `SerialConnectionMinimalConfigModel` |
| `utilities/modbus.py` | `config.defaults` | `DEFAULT_TIMEOUT`, `DEFAULT_FRAMER` |
| `virtual/virtual_serial_network.py` | `virtual.worker` | `create_serial_network` |
| `virtual/virtual_serial_network.py` | `config` | `SerialConnectionMinimalConfig` |
| `virtual/virtual_serial_pair.py` | `virtual.virtual_serial_network` | `VirtualSerialNetwork` |
| `virtual/virtual_serial_pair.py` | `config` | `SerialConnectionMinimalConfig` |
| `__init__.py` | `version`, `config`, `virtual`, `client`, `server` | public re-exports |

## Dependency direction

- **`config` is the root of the intra-package graph.** It imports nothing from
  the package. Every other subsystem that needs a connection type depends on it.
- **`utilities.modbus` sits between `config` and the endpoints.** It is the only
  module that converts config objects into pymodbus parameters.
- **`client` and `server` are siblings.** Neither imports the other. They share
  `config` and `utilities.modbus` but are otherwise independent.
- **`virtual` is orthogonal to the Modbus stack.** It depends only on `config`
  (for external-port descriptors). No Modbus module imports `virtual`, and
  `virtual` imports no Modbus module. The coupling is runtime-only (device
  paths).
- **`utilities.numeric`, `utilities.checksum`, `utilities.mock`,
  `utilities.serial_port_finder` are leaves** with no intra-package imports.
- **`version` is a leaf** imported only by `server` and the package root.

## Core → infrastructure dependencies

| Core module | Infrastructure it depends on |
| --- | --- |
| `client/rs485_client.py` | `pymodbus` (`AsyncModbusSerialClient`, `ModbusPDU`, `DecodePDU`, `FramerBase`) |
| `server/rs485_server.py` | `pymodbus` (`ModbusSerialServer`, `ModbusServerContext`, `ModbusDeviceContext`, `ModbusDeviceIdentification`, `ModbusPDU`, `DecodePDU`, `FramerBase`), `asyncio` |
| `server/modbus_datablock.py` | `pymodbus` (`ModbusSequentialDataBlock`) |
| `utilities/modbus.py` | `pymodbus` (`ModbusException`, `FramerType`, `FRAMER_NAME_TO_CLASS`, `TransactionManager`, `AsyncModbusSerialClient`) |
| `virtual/worker.py` | `pyserial` (`serial.Serial`), stdlib `pty`/`selectors`/`multiprocessing`/`signal` |
| `utilities/serial_port_finder.py` | `pyserial` (`serial.tools.list_ports`) |

`pymodbus` is the single dominant external dependency; it is confined to
`client`, `server`, and `utilities.modbus`. `pyserial` is used directly in
`virtual/worker.py` and `utilities/serial_port_finder.py` (and transitively by
pymodbus's `serial` extra).

## Cross-module dependencies (summary)

- `client` → `config`, `utilities.modbus`, `utilities.numeric`
- `server` → `config`, `utilities.modbus`, `version`, `server.modbus_datablock`
- `virtual` → `config`, `virtual.worker`
- `utilities.modbus` → `config`, `config.defaults`
- package root → all four subsystems + `version`

## Circular dependencies

**None detected** in the intra-package import graph. The graph is a DAG rooted at
`config`/`version`/leaf utilities.

Note (interpretation): `client` and `server` both depend on `utilities.modbus`,
and `utilities.modbus` depends on `config`; there is no back-edge from
`utilities` to `client`/`server`, so no cycle exists.

## Important dependency chains

1. **Client request chain**:
   `RS485Client.read_registers` → `utilities.modbus.modbus_read_registers` →
   `AsyncModbusSerialClient` (pymodbus) → serial port.
2. **Client value-conversion chain**:
   `RS485Client.read_two_registers_float` → `read_two_registers_int` →
   `utilities.numeric.combine_32bit` / `to_signed32` / `float_from_int`.
3. **Server startup chain**:
   `RS485Server.start` → `utilities.modbus.modbus_connection_config` →
   `ModbusSerialServer` (pymodbus) → `asyncio.create_task(serve_forever)`.
4. **Virtual network startup chain**:
   `VirtualSerialNetwork.start` → `multiprocessing.Process(create_serial_network)`
   → `worker.generate_virtual_ports` → `pty.openpty` → `Pipe` responses back to
   parent.
5. **Config serialization chain**:
   `VirtualSerialNetwork.start`/`add` → `SerialConnectionMinimalConfig.to_dict`
   → dict sent over `Pipe` → `worker.add_external_ports` → `serial.Serial(**dict)`.

## Dependency-direction observations (facts)

- `config` has zero outgoing intra-package edges — it is the most stable module.
- `utilities.modbus` is imported by both endpoints but imports only `config`;
  it is a shared lower layer, not a peer.
- `virtual` is not reachable from the Modbus stack; it is a test/example
  substrate. Removing `virtual` would not break `client`/`server` imports.
- `utilities.checksum` is used only by examples/tests, not by `src/` modules —
  it is effectively outside the runtime dependency graph of the library core.
