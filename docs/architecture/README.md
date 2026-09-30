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
  built-in virtual serial network for hardware-free testing.
- **Package**: `scietex.hal.serial`, `src/` layout, implicit namespace packages
  (`scietex/` and `hal/` have no `__init__.py`).
- **Runtime**: Linux/macOS only. The virtual layer uses `pty.openpty` and
  `multiprocessing`; it does not run on Windows.
- **Python**: `requires-python = ">=3.10"` (`pyproject.toml`); README claims 3.9
  (stale). tox targets `py314`; CI matrix is 3.10/3.12/3.14.
- **Core third-party dependency**: `pymodbus[serial] ~= 3.12` (client, server,
  framers, PDU, datastore). `pyserial` arrives transitively via the `serial`
  extra and is imported directly in `virtual/worker.py` and
  `utilities/serial_port_finder.py`.
- **Public API**: re-exported from `src/scietex/hal/serial/__init__.py`
  (`__all__` lists 9 symbols).
- **Version**: dynamic, read from `src/scietex/hal/serial/version.py`
  (`__version__ = "1.3.0"`).

## Source size (verified)

| Area | Files | Lines |
| --- | --- | --- |
| `src/scietex/hal/serial/` | 20 `.py` | ~3,900 |
| `tests/` | 15 `.py` | ~2,534 |
| `examples/` | 8 `.py` | ~734 |

Largest source modules: `utilities/modbus.py` (637), `client/rs485_client.py`
(664), `virtual/worker.py` (559), `config/serial_connection_implementation.py`
(491), `utilities/numeric.py` (388), `virtual/virtual_serial_network.py` (362).
