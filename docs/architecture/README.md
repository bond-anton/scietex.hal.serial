# Architecture Map — `scietex.hal.serial`

Factual structural map of the repository, produced for a later deep architectural
review. This is **not** a review: it records what exists, where, and how the parts
connect. Interpretations are marked as such; unknowns are marked `UNKNOWN`.

## Index

| Document | Contents |
| --- | --- |
| [`overview.md`](overview.md) | Subsystems, responsibilities, interactions, entry points, runtime processes |
| [`structure.md`](structure.md) | Directory/package layout, module responsibilities, boundaries |
| [`components.md`](components.md) | Per-component purpose, classes/functions, interfaces, dependencies |
| [`dependencies.md`](dependencies.md) | Dependency direction, cross-module edges, cycles, chains |
| [`data-flow.md`](data-flow.md) | Major data flows, transformations, async/process boundaries |
| [`lifecycle.md`](lifecycle.md) | Startup, operation, shutdown, cleanup, workers, resource ownership |
| [`hotspots.md`](hotspots.md) | Areas warranting deeper architectural investigation |

## Project at a glance

- **What**: Python library for serial/Modbus (RS485) communication, with a
  built-in virtual serial network for hardware-free testing and a serial↔TCP
  Modbus gateway.
- **Package**: `scietex.hal.serial`, `src/` layout, implicit namespace packages
  (`scietex/` and `hal/` have no `__init__.py`).
- **Runtime**: Linux/macOS only. The virtual layer uses `pty.openpty` and
  `multiprocessing`; it does not run on Windows.
- **Python**: `requires-python = ">=3.10"` (`pyproject.toml`). tox `env_list` is
  `format, lint, type, py{310,312,314}`; the CI matrix is 3.10/3.12/3.14.
- **Core third-party dependency**: `pymodbus[serial] ~= 3.15` (client, server,
  gateway, framers, PDU, datastore). `pyserial` arrives transitively via the
  `serial` extra and is imported directly in `virtual/worker.py` and
  `utilities/serial_port_finder.py`.
- **Gateway**: the `gateway/` package is a frame-level serial↔TCP Modbus proxy.
  `ModbusGateway` owns one serial port via `AsyncModbusSerialClient`;
  `GatewayTcpServer` accepts standard Modbus/TCP clients; requests are routed
  by device id, swapping the serial framer per device under an `asyncio.Lock`.
- **Public API**: re-exported from `src/scietex/hal/serial/__init__.py`
  (`__all__` lists 26 symbols, including the 7 gateway symbols `ModbusGateway`,
  `GatewayConfig`, `GatewayDeviceConfig`, `GatewayTcpServer`,
  `GatewayTranslator`, `GatewayError`, `GatewayConfigError`).
- **Version**: dynamic, read from `src/scietex/hal/serial/version.py`
  (`__version__ = "2.0.0"`).

## Source size (verified)

| Area | Files | Lines |
| --- | --- | --- |
| `src/scietex/hal/serial/` | 31 `.py` | ~5,766 |
| `tests/` | 33 `.py` | ~4,040 |
| `examples/` | 8 `.py` | ~714 |

Largest source modules: `utilities/modbus.py` (789), `client/rs485_client.py`
(784), `virtual/worker.py` (554), `config/serial_connection_implementation.py`
(486), `virtual/virtual_serial_network.py` (424), `utilities/numeric.py` (384).
