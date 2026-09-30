# Overview

## Purpose

`scietex.hal.serial` is a serial/Modbus communication library. It provides:

1. Dataclass-style serial connection configuration with validation.
2. A virtual serial network (pseudo-terminal based) for testing without hardware.
3. A Modbus/RS485 server (`RS485Server`).
4. A Modbus/RS485 client (`RS485Client`).
5. Numeric/checksum/Modbus helper utilities.

## Major subsystems

| Subsystem | Package | Responsibility |
| --- | --- | --- |
| Configuration | `config/` | Typed serial connection configs, validation, defaults, config exception |
| Virtual serial | `virtual/` | Create/manage virtual serial ports and forward bytes between them |
| Server | `server/` | Modbus serial server + reactive datablock |
| Client | `client/` | Async Modbus serial client with typed register helpers |
| Utilities | `utilities/` | Modbus connection/IO helpers, numeric conversions, checksums, port finder, test mocks |

## Responsibilities and interactions

- **`config`** is the shared vocabulary. `SerialConnectionMinimalConfigModel` and
  its subclasses are the type accepted by `virtual`, `server`, `client`, and
  `utilities.modbus`. `config` depends on nothing else in the package.
- **`utilities.modbus`** translates a config object into pymodbus parameters and
  wraps pymodbus client calls. It depends on `config` (and `config.defaults`).
- **`client`** composes `utilities.modbus` (transport) and `utilities.numeric`
  (value conversion) behind a typed API. It depends on `config`,
  `utilities.modbus`, `utilities.numeric`.
- **`server`** composes pymodbus server primitives with `utilities.modbus`
  (connection config) and its own `ReactiveSequentialDataBlock`. It depends on
  `config`, `utilities.modbus`, `version`.
- **`virtual`** is independent of Modbus. It depends only on `config` (for
  external-port descriptors) and the standard library (`pty`, `multiprocessing`,
  `selectors`, `signal`). It is the substrate used by tests and examples to give
  server/client a real byte pipe.
- **`utilities.numeric`, `utilities.checksum`, `utilities.serial_port_finder`,
  `utilities.mock`** are leaf modules with no intra-package dependencies
  (`serial_port_finder` depends on `pyserial`; `mock` depends on nothing).

Interaction summary (interpretation): `config` is the hub type; `client` and
`server` are the two protocol endpoints; `virtual` is the transport substitute
used to connect them in tests/examples; `utilities` supports both endpoints.

## Application entry points

This is a **library**, not an application. There is no `main()` in `src/`.
Entry points are:

- **Public API import**: `from scietex.hal.serial import ...`
  (`src/scietex/hal/serial/__init__.py`).
- **Examples** (`examples/`, runnable scripts with `if __name__ == "__main__":`):
  - `config.py` — config construction/serialization.
  - `virtual_serial_pair.py`, `virtual_serial_network.py`,
    `virtual_serial_network2.py` — virtual network usage.
  - `modbus_server.py`, `modbus_client.py` — server/client over a virtual pair.
  - `rs485_custom_request.py` — custom framer/decoder/PDU example (365 lines).
  - `find_serial_ports.py` — VID/PID port discovery.
- **Tests** (`tests/`) exercise the library through the same public API.

## Runtime processes

- **Main process**: hosts `RS485Server` (asyncio task), `RS485Client` (async
  calls), and the `VirtualSerialNetwork` parent-side API.
- **Worker process**: `virtual/worker.py:create_serial_network` runs in a
  separate `multiprocessing.Process` spawned by
  `VirtualSerialNetwork.start()`. It owns the pty master file descriptors and
  runs the `selectors`-based forwarding loop. It blocks `SIGINT`/`SIGTERM` so the
  parent controls shutdown.
- **IPC**: a `multiprocessing.Pipe()` pair (`__master_io` in the parent,
  `__worker_io` in the worker) carries command/response dicts.
- **Async boundary**: `RS485Server` runs `ModbusSerialServer.serve_forever()` in
  an `asyncio.Task`; `RS485Client` methods are `async` and drive pymodbus's
  `AsyncModbusSerialClient`.

## Key runtime facts

- The virtual worker forwards every byte received on one port to **all other**
  ports (broadcast), unless `loopback=True`, in which case the sender also
  receives it (`worker.py:forward_data`).
- `RS485Client` opens and closes the underlying serial connection **per
  operation** (`utilities/modbus.py:modbus_execute` / `modbus_read_registers` /
  `modbus_write_registers` call `client.connect()` then `client.close()`).
- `RS485Server.update_slave` / `remove_slave` rebuild the `ModbusServerContext`
  and **restart** the server when it is running.
