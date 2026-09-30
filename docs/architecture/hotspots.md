# Hotspots

Areas warranting deeper architectural investigation. Each entry states the
**fact** observed and the **question** it raises. No refactor proposals are made
here — this is a scoping aid for the later review.

---

## H1. Per-operation connect/close in the client

**Fact**: `utilities.modbus.modbus_execute`, `modbus_read_registers`,
`modbus_write_registers`, and `modbus_write_register` each call
`await client.connect()` and `await client.close()` around a single operation.
`RS485Client` has no long-lived connection and no explicit `close()`.

**Question**: what is the cost and failure behavior of reconnecting on every
register access, and how does it interact with the server's per-request
handling? Relevant for throughput and error recovery.

**Files**: `utilities/modbus.py`, `client/rs485_client.py`.

---

## H2. Server restart on every context mutation

**Fact**: `RS485Server.update_slave` and `remove_slave` rebuild
`self.context` and `await self.restart()` when the server is running. `restart`
is `stop()` + `start()`.

**Question**: does restarting the pymodbus server drop in-flight requests or
reopen the serial port, and is that acceptable for dynamic slave management?

**Files**: `server/rs485_server.py`.

---

## H3. Parent/worker response-count coupling

**Fact**: `VirtualSerialNetwork.start` blocks on exactly
`virtual_ports_num + len(external_ports)` `recv()` calls; `add`/`create`/`remove`
similarly block on a fixed count. The worker sends one response per item.

**Question**: what happens if the worker sends a different number of responses
(e.g. an error path that skips a response)? Is there a timeout or desync guard?

**Files**: `virtual/virtual_serial_network.py`, `virtual/worker.py`.

---

## H4. `stop()` robustness

**Fact**: `VirtualSerialNetwork.stop()` guards on `__p is not None`, sends the
`stop` command, calls `__p.join(timeout=5)`, then drops the `Process` object
(without `close()`), nulls the pipes, and resets `serial_ports`. It does not
restore the previous `SIGTERM`/`SIGINT` handlers and does not remove the
data-log directory.

**Question**: if the worker does not exit within the 5s join timeout, the
process is abandoned rather than killed — what happens to its pty fds and
external serial handles? Are handlers leaked across repeated start/stop cycles?

**Files**: `virtual/virtual_serial_network.py`.

---

## H5. Broadcast forwarding semantics

**Fact**: `worker.forward_data` writes each received chunk to every other master
fd (or all, with `loopback=True`). There is no addressing, framing, or
back-pressure.

**Question**: for networks with more than two ports, does broadcast forwarding
match the intended topology, and can a slow reader cause unbounded buffering?

**Files**: `virtual/worker.py`.

---

## H6. Data-logging growth and framing

**Fact**: `setup_data_logging` uses a `RotatingFileHandler` (10 MB × 5) and
splits the byte stream on `data_logging_splitter`; `master_cache` accumulates
bytes per fd until a splitter is seen.

**Question**: can `master_cache` grow unbounded if the splitter never appears?
Is the log format (hex + repr) sufficient for the intended diagnostics?

**Files**: `virtual/worker.py`.

---

## H7. Config validation surface

**Fact**: `config/validation.py` validates port, baudrate, bytesize, parity,
stopbits, timeout, framer. `SerialConnectionMinimalConfig` validates in
`__init__` and every setter. `to_dict()` shapes differ per class (5/7/8 keys).

**Question**: are the allowed-value sets in `config/defaults.py` complete and
consistent with pymodbus's accepted values? Do the differing `to_dict()` shapes
cause issues when passed to `serial.Serial(**dict)`?

**Files**: `config/validation.py`, `config/defaults.py`,
`config/serial_connection_implementation.py`, `virtual/worker.py`.

---

## H8. `utilities.modbus` error handling

**Fact**: `modbus_read_registers`/`modbus_write_registers` catch
`ModbusException` and return `None`; `modbus_execute` returns `None` on
exception. Callers in `RS485Client` treat `None` as "no response" and may fall
back to a read-back.

**Question**: is `None` an unambiguous signal across all call sites, and are
distinguishable error conditions (timeout vs. exception vs. empty response)
collapsed in a way that hides failures?

**Files**: `utilities/modbus.py`, `client/rs485_client.py`.

---

## H9. Custom protocol injection points

**Fact**: `RS485Server` accepts `custom_pdu`/`custom_framer`/`custom_decoder`;
`RS485Client` accepts `custom_framer`/`custom_decoder`/`custom_response`. The
example and test implement a full custom ASCII/LRC protocol.

**Question**: how much of the pymodbus contract must a custom implementation
satisfy, and is that contract documented anywhere in the repo?

**Files**: `server/rs485_server.py`, `client/rs485_client.py`,
`examples/rs485_custom_request.py`, `tests/server/test_custom_request.py`.

---

## H10. `virtual` is untested against the Modbus stack directly

**Fact**: `virtual` has no import edge to `client`/`server`; integration is
exercised only through tests/examples that wire them together at runtime.

**Question**: is there a single canonical integration test that covers the full
client↔virtual↔server path, or is coverage split across separate test modules?

**Files**: `tests/virtual/`, `tests/server/`, `tests/client/`,
`tests/conftest.py`.

---

## H11. Version and packaging inconsistencies

**Fact**: `version.py` holds `__version__ = "1.3.0"`; `pyproject.toml` reads it
dynamically. CI installs `.[all,test]` but no `all` extra exists (only `dev`,
`test`, `lint`). tox targets `py314`; CI matrix is 3.10/3.12/3.14; README says
3.9. `pytest.ini` overrides `pyproject.toml` `pythonpath`.

**Question**: which Python versions are actually supported, and does CI pass as
configured?

**Files**: `pyproject.toml`, `tox.ini`, `pytest.ini`, `README.md`,
`.github/workflows/python-package.yml`, `.github/workflows/pylint.yml`.

---

## H12. `utilities.checksum` outside the runtime graph

**Fact**: `utilities/checksum.py` (`check_sum`, `lrc`, `check_lrc`) is not
imported by any `src/` module; it is used by the custom-protocol example and
tests.

**Question**: is `checksum` intended as public API (it is not re-exported at the
package root) or as an example/test helper?

**Files**: `utilities/checksum.py`, `examples/rs485_custom_request.py`,
`tests/utilities/`.

---

## H13. Signal handling and shutdown races

**Fact**: the parent installs `SIGTERM`/`SIGINT` handlers that call `stop()`; the
worker blocks `SIGINT`/`SIGTERM`. `stop()` sends the stop command, joins with a
5s timeout, and drops the pipes.

**Question**: what happens if a signal arrives during `start()` (before `__p` is
assigned) or during an `add`/`remove` `recv()`? Is there a race between the
signal handler and the main thread's pipe operations?

**Files**: `virtual/virtual_serial_network.py`, `virtual/worker.py`.

---

## H14. Test timeout vs. worker startup

**Fact**: `pytest-timeout` is set to 10s with `timeout_method = signal`; tests
that spawn the virtual worker must finish within 10s. The worker's
`forward_data` uses a 1s `select` timeout.

**Question**: is 10s sufficient for all worker-spawning tests on slow CI, and
does the 1s select timeout interact with test timing?

**Files**: `pytest.ini`, `tests/virtual/`, `virtual/worker.py`.
