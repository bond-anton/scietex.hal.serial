# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `GatewayConfig.bus_timeout` bounds how long one request may hold the shared
  serial bus, and `GatewayConfig.request_timeout` bounds how long a client may
  wait for it. Both default to values derived from the serial timeout, the
  retry count, and `bus_queue_depth` (new, default `4`), which is the number of
  queued clients the lock-wait budget tolerates. The lock-wait derivation is
  `(bus_timeout + 2 * serial_timeout + 0.1) * (bus_queue_depth + 1) +
  serial_timeout`: it budgets one hold per client ahead plus the single resync
  (reconnect and quarantine) a dirty bus may add. A request that cannot acquire
  the bus in time now returns exception `0x06` (server device busy) instead of
  `0x0B` (gateway target failed), because the target device was never addressed.
- `GatewayConfig.client_timeout_floor` publishes the lower bound a client must
  exceed for its per-request socket timeout:
  `request_timeout + bus_timeout + 2 * serial_timeout + 0.1`. A client that
  times out first sees only its own library timeout -- no Modbus exception PDU
  and no gateway metric, since the gateway cannot observe the disconnect -- and
  its request may still be executing, so a retry queues behind it. The floor is
  computed once at construction from the concretized budgets, so mutating
  `request_timeout`/`bus_timeout` afterwards cannot publish a floor that
  disagrees with the budgets the gateway actually enforces. The resync
  response window (`GatewayConfig.resync_window`) is validated at construction
  like the other budgets: zero, negative, non-finite, and non-numeric values are
  rejected.

### Fixed

- A request that outlives the hold budget no longer poisons the next one. The
  abandoned transaction is cancelled mid-wire, and RTU frames carry no usable
  transaction id, so the device's late reply used to be accepted as the answer
  to the next request for the same device id. The gateway now marks the bus
  dirty on expiry, closes and reopens the transport before the next request,
  and lets the remainder of the response window expire before transmitting.
  The quarantine is recomputed after the reopen, so the connect overhead is not
  added to it, and the dirty flag is cleared once the reopen and the window have
  completed -- not only after the following transaction succeeds. A failing
  transaction after a successful resync no longer reconnects before every later
  request.
- A device that answers with a Modbus exception response is no longer counted
  as a failure by the circuit breaker. It responded, so it is alive; counting
  device exceptions let any network peer open a healthy device's breaker, and
  `isError()` also flags vendor PDUs whose normal function code exceeds `0x80`.
- The dirty-bus mark is armed on every cancellation path of the cleanup that
  follows an abandoned transaction, not just when the cleanup completes. A
  second cancellation (a shutdown, or a pymodbus transaction that swallows the
  first one and finishes later) used to skip the mark, which let a late reply
  answer the next request for the same device id. `stop()` also clears the
  resync state, so a restarted gateway does not pay a close/reopen and the
  quarantine sleep on its first request.
- The gateway example derives its client timeout from
  `GatewayConfig.client_timeout_floor` instead of a hard-coded 1 s, which was
  below the floor its own configuration published.
- A lock-wait rejection (`0x06`) is no longer booked as a device error in the
  gateway metrics: no device failed, and `GatewayMetrics.errors` documents
  gateway-level `0x0B` failures. The request is still counted by
  `record_request`; there is no separate busy counter.

## [2.6.0] - 2026-11-05

### Added

- Two generic driver descriptors, `standard_rtu` and `standard_ascii`. A device
  that speaks plain Modbus picks one of these and carries its own identity in
  the device name.

### Removed

- The five vendor-named descriptors (`scietex_ftmone`, `cyky_tm106b`,
  `intek_spe_b`, `vesper_e5_8200`, `vesper_e4_8400`). Each was a frozen
  dataclass whose only non-empty field was the framer, so it named a protocol
  shape rather than a device. A descriptor is now reserved for a device the
  gateway cannot route without vendor code — a translator, a custom framer, or
  custom PDUs — and those live in the vendor package.

  A database that stored one of the old names needs
  `scripts/migrate_generic_driver_names.py` from `scietex.api156.equipment.modbus`
  before its devices are edited again.

## [2.5.0] - 2026-11-05

### Added

- Built-in driver descriptors for the Intek SPE-B and the Vesper E5-8200 /
  E4-8400 drives (`intek_spe_b`, `vesper_e5_8200`, `vesper_e4_8400`). All three
  speak standard Modbus RTU, so the gateway routes them with the built-in RTU
  framer and no translator — the same shape as the film thickness monitors.

### Changed

- A gateway descriptor is now built in whenever the device speaks plain Modbus
  and the gateway needs no vendor code to route it. Previously the VFD
  descriptors lived in `scietex.hal.vfd`, which forced every gateway image to
  install that package as an extra even though the gateway imports nothing from
  it. An extra is now reserved for devices whose protocol the gateway cannot
  frame without vendor code.

## [2.0.2] - 2026-10-07

### Fixed

- `ModbusGateway` now reconnects the serial bus on the next request when the
  transport is down. Previously a gateway whose initial connect failed never
  recovered: the pymodbus client's `execute` raises `ConnectionException` when
  the transport is missing instead of reconnecting, so every request returned
  exception `0x0B` even after the port became available. The gateway now calls
  `connect()` itself before forwarding (`_ensure_connected`). This covers a port
  that is absent at startup, a port that disappears after a healthy start, and a
  port that cannot be opened for lack of permission (`EACCES`) — in every case
  the next request after the port is usable reconnects and succeeds.

## [2.0.1] - 2026-10-07

### Fixed

- `ModbusGateway.start()` no longer reports a healthy start when the serial port
  cannot be opened. It now checks the connect result and logs a warning
  (`Gateway bus could not be opened on <port>; will retry on the next request`)
  instead of `Gateway bus opened on <port>`. Startup still succeeds; the gateway
  reconnects on the next request (see the `[Unreleased]` fix).

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
