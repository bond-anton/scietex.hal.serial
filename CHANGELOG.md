# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `ModbusGateway.start()` no longer reports a healthy start when the serial port
  cannot be opened. It now checks the connect result and logs a warning
  (`Gateway bus could not be opened on <port>; will retry on the next request`)
  instead of `Gateway bus opened on <port>`. Startup still succeeds — the client
  reconnects on the next request.

## [2.0.0] - 2026-10-01

### Added

- **Modbus Gateway** (`gateway` module): bridges a serial RS485 bus to TCP/IP,
  routing Modbus/TCP requests to devices by id. Supports non-Modbus vendor
  protocols through translator plugins (`GatewayTranslator`), custom framers,
  decoders, and PDU classes resolved by dotted path. Public API:
  `ModbusGateway`, `GatewayTcpServer`, `GatewayConfig`, `GatewayDeviceConfig`,
  `GatewayTranslator`, `GatewayError`, `GatewayConfigError`.
- `ModbusOperationError` exception, exported from the package root.
- `modbus_connection` async context manager for connection reuse.
- Overridable hardware VID/PID profiles in `find_serial_ports` and the
  `find_stm32_cdc` / `find_rs485` helpers.
- Configurable retries on the Modbus client.
- Virtual serial worker supervision: a dead worker now raises
  `VirtualSerialNetworkError` on the next command instead of hanging, and
  `stop()` tolerates an already-dead worker.
- MkDocs Material documentation site with a user guide, API reference,
  architecture notes, and design docs, published on Read the Docs.

### Changed

- **Breaking: strict error contract by default.** Read, write, and execute
  operations now raise `ModbusOperationError` on failure instead of returning
  `None`. Pass `raise_on_error=False` to restore the 1.x behavior, including the
  write→read fallback. See the
  [upgrading guide](https://scietex-hal-serial.readthedocs.io/en/latest/guide/upgrading/).
- **Breaking: `None` is no longer a failure sentinel.** It now only means "no
  response was expected" (`no_response_expected=True`).
- **Breaking: the write→read fallback is opt-in.** It runs only when
  `raise_on_error=False` is passed.
- Minimum `pymodbus` raised to `~= 3.15`.
- Tooling migrated to `uv`, `ruff`, and `ty`; tests run in parallel with
  `pytest-xdist`.
- `utilities/mock.py` is no longer part of the shipped package; the mock helper
  now lives under `tests/`.

### Fixed

- Successful FC16 multi-register writes no longer raise spuriously.
- Zero-value writes and reads are no longer misclassified as failures.
- `rs485_custom_request` example updated for the pymodbus 3.15 datastore API.
- Assorted docstring, type-annotation, and documentation corrections.

### Removed

- Stale `pylint` disable comments and a dead reactive datablock callback.

[Unreleased]: https://github.com/bond-anton/scietex.hal.serial/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/bond-anton/scietex.hal.serial/compare/v1.3.0...v2.0.0
