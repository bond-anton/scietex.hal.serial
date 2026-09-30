# Lifecycle

Startup, operation, shutdown, cleanup, and resource ownership for each
stateful component.

---

## 1. `VirtualSerialNetwork` (parent side)

**Construction** (`__init__`):
- Stores `virtual_ports_num`, `external_ports`, `loopback`, `logger`,
  `data_log_dir`, `data_logging_splitter`.
- Initializes `serial_ports = []`, `__master_io = None`, `__worker_io = None`,
  `__p = None`.
- If `data_log_dir` is set, creates the directory and sets
  `data_logging_file = data_log_dir / "vsn-data.log"`.

**Startup** (`start(openpty_func=None)`):
1. Installs `signal.signal(SIGTERM, self._signal_handler)` and
   `signal.signal(SIGINT, self._signal_handler)`.
2. If `__p is not None`: logs "already running" and returns (idempotent guard).
3. Creates `__master_io, __worker_io = multiprocessing.Pipe()`.
4. Serializes `external_ports` via `to_dict()`.
5. Creates `__p = multiprocessing.Process(target=create_serial_network, args=(__worker_io, virtual_ports_num, external_ports, loopback, openpty_func, logger, data_logging_file, data_logging_splitter))`.
6. `__p.start()`; resets `virtual_ports_num = 0`.
7. Receives `virtual_ports_num` responses for virtual ports; appends each `OK`
   `payload` to `serial_ports` and increments `virtual_ports_num`.
8. Receives `len(external_ports)` responses for external ports; collects `OK`
   payloads into `ports_connected`.
9. `_update_ext_ports(ports_connected)` and `_ext_ports_remove_duplicates()`
   prune `external_ports`; `serial_ports += ports_connected`; then
   `serial_ports = list(set(serial_ports))` (deduplicated).

**Operation**:
- `add(external_ports)` — sends `add` command, receives one response per port,
  updates `external_ports` and `serial_ports`.
- `create(ports_num)` — sends `create`, receives `ports_num` responses, updates
  `virtual_ports_num` and `serial_ports`.
- `remove(remove_list)` — sends `remove`, receives one response per name,
  removes from `serial_ports`/`external_ports`, decrements `virtual_ports_num`
  for virtual ports.

**Shutdown** (`stop()`):
1. If `__p is None`: returns (no-op guard).
2. Sends `{"cmd": "stop"}` over `__master_io` (if truthy).
3. `__p.join(timeout=5)`.
4. Sets `__p = None`, `__master_io = __worker_io = None`, `serial_ports = []`.

**Signal handling**: `_signal_handler(signum, frame)` calls `self.stop()`; both
`SIGTERM` and `SIGINT` are wired to it in `start()`.

**Resource ownership**: parent owns the `Process` handle and both `Pipe` ends;
the worker owns the pty master fds and `serial.Serial` objects for external
ports.

**Cleanup gaps (facts)**:
- `stop()` does not call `__p.close()` (the `Process` object is dropped, not
  explicitly closed).
- `stop()` does not remove the `data_log_dir` or the log file.
- `stop()` does not restore the previous `SIGTERM`/`SIGINT` handlers.
- `stop()` uses `join(timeout=5)`; if the worker does not exit within 5s, the
  process is abandoned (not killed) and the pipes are dropped.

---

## 2. `VirtualSerialPair`

**Construction**: `VirtualSerialPair(external_ports=None, loopback=False, logger=None, data_log_dir=None, data_logging_splitter=None)` → calls
`super().__init__(virtual_ports_num=2, ...)`.

**Startup** (`start`): if `len(serial_ports) < 2`, calls `stop()` first, then
`super().start()`.

**Operation**: `add`/`create`/`remove` are overridden to no-ops (fixed pair).

**Shutdown**: inherits `stop()`.

---

## 3. Virtual worker process (`create_serial_network`)

**Startup**:
1. Blocks `SIGINT`/`SIGTERM` via `signal.pthread_sigmask(SIG_BLOCK, ...)`.
2. Enters `with Selector() as selector, ExitStack() as stack:`.
3. `generate_virtual_ports(...)` — for each of `ports_number`: `pty.openpty()`,
   set raw mode on the slave, register the master with the selector, and
   `stack.enter_context(master_files[master_fd])`; send
   `{"status": "OK", "payload": <slave_name>}` per port.
4. `add_external_ports(...)` — for each external config dict: open
   `serial.Serial(**config)`, register its fd, `stack.enter_context(...)`, send
   status per port.
5. Enters the main loop: `while keep_running: keep_running = process_cmd(...); forward_data(...)`.

**Operation**: `process_cmd` polls `worker_io` (non-blocking) for commands;
`forward_data` runs one `selector.select(timeout=1)` cycle and forwards bytes.
`setup_data_logging(...)` (called from `forward_data` when a log file is set)
creates a `RotatingFileHandler` (10 MB × 5) and a `logging.Logger`.

**Shutdown**:
- `process_cmd` returns `False` on `{"cmd": "stop"}` → loop exits.
- The `with` block unwinds: `ExitStack` closes every registered master file and
  external `serial.Serial`; `Selector.__exit__` closes the selector.
- `worker_io` is closed by the parent side / process teardown.

**Resource ownership**: worker owns pty masters, external serial handles,
selector, and the logging handler.

---

## 4. `RS485Server`

**Construction** (`__init__`):
- Stores `con_params`, `custom_pdu`, `custom_framer`, `custom_decoder`,
  `logger`.
- Builds `devices` from the `devices` argument (or empty dict).
- Builds `context = ModbusServerContext(devices=..., single=False)`.
- Builds `identity = ModbusDeviceIdentification(info_name=SERVER_INFO)`.
- `server = None`, `_task = None`.

**Startup** (`async start()`):
- If `self.server is not None`: no-op (idempotent guard).
- `self.server = ModbusSerialServer(context=self.context, identity=self.identity, custom_pdu=self.custom_pdu, **modbus_connection_config(self.con_params))`.
- If `custom_decoder`: `self.server.decoder = custom_decoder(is_server=True)` and
  registers each `custom_pdu`.
- If `custom_framer`: `self.server.framer = self.custom_framer`.
- `self._task = asyncio.create_task(self.server.serve_forever())`.

**Operation**:
- `update_slave(slave_id, store)` — sets `devices[slave_id]`, rebuilds
  `context`, `await restart()` if `_task` is set.
- `remove_slave(slave_id)` — pops from `devices`, rebuilds `context`,
  `await restart()` if `_task` is set.

**Shutdown** (`async stop()`):
- If `_task is not None`: if `server` is active, `await server.shutdown()`;
  `_task.cancel()`; `await _task` (swallowing `CancelledError`); set
  `_task = None` when done.
- `self.server = None`.

**Restart** (`async restart()`): `await stop()` then `await start()`.

**Resource ownership**: server owns the pymodbus `ModbusSerialServer` and the
asyncio task; the serial port is opened/closed by pymodbus.

**Cleanup gaps (facts)**:
- `update_slave`/`remove_slave` restart the whole server, dropping in-flight
  requests.
- `update_slave` validates `0 < slave_id < 248`; `remove_slave` silently warns
  if the id is absent.

---

## 5. `RS485Client`

**Construction** (`__init__`):
- Stores `con_params`, `address`, `label`, `custom_*`, `logger`.
- `__read_chunk_size = chunk_size`, `__write_chunk_size = write_chunk_size`.
- Builds `self.client = modbus_get_client(con_params, custom_framer, custom_decoder, custom_response, label)`.

**Operation**:
- Each public method calls `utilities.modbus.*`, which does
  `await client.connect()` … `await client.close()` per call.
- Setting `con_params` or `label` rebuilds `self.client` via
  `modbus_get_client`.

**Shutdown**: there is **no explicit `close()`/`disconnect()` method** on
`RS485Client`. The underlying client is connected and closed inside each
operation; no long-lived connection is held.

**Resource ownership**: `RS485Client` owns the `AsyncModbusSerialClient`
instance; the serial port is opened/closed per operation by `utilities.modbus`.

---

## 6. Configuration objects

**Lifecycle**: constructed with keyword args; every setter validates and raises
`SerialConnectionConfigError` on invalid input. `to_dict()` produces the
serialization used across the process boundary. No explicit teardown.

---

## Lifecycle ordering (end-to-end, tests/examples)

1. `VirtualSerialPair(...)` → `start()` → worker process spawns, pty ports
   created, `serial_ports` populated.
2. `RS485Server(ModbusSerialConnectionConfig(serial_ports[0]))` → `await start()`
   → pymodbus server task running.
3. `RS485Client(ModbusSerialConnectionConfig(serial_ports[1]), address=1)` →
   per-call connect/close.
4. `await server.stop()` → pymodbus shutdown.
5. `pair.stop()` → worker `stop` command, process joined, pipes closed.

**Ordering constraint (fact)**: the virtual network must be started before the
server/client are constructed with its port names; the server must be stopped
before the virtual network is stopped.

---

## Signal handling

| Process | Handler | Effect |
| --- | --- | --- |
| Parent | `signal.signal(SIGTERM/SIGINT, VirtualSerialNetwork._signal_handler)` | calls `stop()` |
| Worker | `signal.pthread_sigmask(SIG_BLOCK, {SIGINT, SIGTERM})` | ignores signals; parent controls shutdown |

The worker deliberately does not handle signals so that only the parent decides
when to stop, avoiding double-shutdown races.

---

## Resource ownership summary

| Resource | Owner | Released by |
| --- | --- | --- |
| pty master fds | worker process | `ExitStack` unwind on loop exit |
| pty slave names | parent (`serial_ports`) | not explicitly removed |
| external `serial.Serial` | worker process | `ExitStack` unwind |
| `multiprocessing.Process` | parent | `stop()` (`join(timeout=5)`; not `close()`d) |
| `Pipe` ends | parent + worker | `stop()` (parent) / process teardown (worker) |
| `ModbusSerialServer` | `RS485Server` | `await stop()` |
| asyncio task | `RS485Server` | `server.shutdown()` |
| `AsyncModbusSerialClient` | `RS485Client` | per-operation `close()` |
| rotating log handler | worker process | process teardown (handler not explicitly closed) |
