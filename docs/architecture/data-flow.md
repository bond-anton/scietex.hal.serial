# Data Flow

Major flows through the system. Each entry lists source, processing components,
destination, transformations, and any async/process boundaries.

---

## Flow 1 — Modbus client read (single register)

**Source**: caller invokes `RS485Client.read_register(register, holding, signed)`.

**Path**:
1. `RS485Client.read_register` → `RS485Client.read_registers(register, count=1, holding)`.
2. `read_registers` → `utilities.modbus.modbus_read_registers(client, start_register, count, device_id=self.address, holding, max_count=__read_chunk_size, logger)`.
3. `modbus_read_registers`:
   - `await client.connect()` (pymodbus `AsyncModbusSerialClient`).
   - loops in chunks of `max_count` (or all at once if `max_count < 1`), calling
     `client.read_holding_registers` or `client.read_input_registers`.
   - `client.close()` in `finally`.
   - collects `response.registers` across chunks; returns `None` on error/empty.
4. Back in `read_registers`: if `signed`, maps each value through
   `utilities.numeric.to_signed16`.
5. `read_register` returns `response[0]` (or `to_signed16(response[0])`).

**Destination**: caller receives `int | None`.

**Transformations**: raw Modbus register words → list[int] → optional signed
16-bit reinterpretation.

**Boundaries**: async (`await` on pymodbus I/O). Connection is opened and closed
per call.

---

## Flow 2 — Modbus client write (single register)

**Source**: `RS485Client.write_register(register, value, signed, no_response_expected)`.

**Path**:
1. If `signed`, `value` → `utilities.numeric.from_signed16(value)`.
2. → `utilities.modbus.modbus_write_register(client, register, value, device_id, logger, no_response_expected)`.
3. `modbus_write_register`: `connect()` → `client.write_register(...)` →
   `close()`; returns `response.registers[0]` or `None`.
4. Back in `write_register`: if response falsy and `no_response_expected=False`,
   falls back to `read_register(register, holding=True, signed=signed)`.

**Destination**: caller receives written value (`int | None`).

**Transformations**: signed→unsigned 16-bit before write; optional read-back.

**Boundaries**: async; per-call connect/close.

---

## Flow 3 — Modbus client 32-bit / float read

**Source**: `RS485Client.read_two_registers_float(start_register, factor, holding, byteorder, signed)`.

**Path**:
1. `read_two_registers_float` → `read_two_registers_int(start_register, count=2, ...)`.
2. `read_two_registers_int` → `read_registers(count=2)` (Flow 1) → two words.
3. `utilities.numeric.combine_32bit(word0, word1, byteorder)` → 32-bit int.
4. If `signed`, `to_signed32`.
5. `read_two_registers_float` → `utilities.numeric.float_from_int(value, factor)`.

**Destination**: caller receives `float | None`.

**Transformations**: two 16-bit words → 32-bit int (endianness-aware) → scaled
float.

**Boundaries**: async; per-call connect/close.

---

## Flow 4 — Modbus server request handling

**Source**: bytes arriving on the server's serial port.

**Path**:
1. `RS485Server.start` builds `ModbusSerialServer(context, identity, custom_pdu, **modbus_connection_config(con_params))` and runs
   `asyncio.create_task(server.serve_forever())`.
2. pymodbus framer decodes the ADU; decoder resolves the PDU; the server
   dispatches to the datastore.
3. Datastore reads/writes go through `ReactiveSequentialDataBlock`:
   - reads: inherited `ModbusSequentialDataBlock` behavior.
   - writes: `setValues(address, values)` → `super().setValues(...)` →
     `on_change(address, values)` (default logs).
4. Response PDU is encoded and written back to the serial port by pymodbus.

**Destination**: Modbus client on the other end of the serial link.

**Transformations**: serial bytes → ADU → PDU → datastore operation → response
PDU → ADU → serial bytes.

**Boundaries**: async task (`serve_forever`). Custom framer/decoder/PDU can be
injected via `RS485Server.__init__`.

**Dynamic context changes**: `update_slave`/`remove_slave` mutate `self.devices`,
rebuild `self.context`, and `await self.restart()` if `_task` is set — i.e. the
server is stopped and started again.

---

## Flow 5 — Virtual serial byte forwarding (worker process)

**Source**: bytes written by any process to a virtual port's slave device.

**Path** (inside `worker.create_serial_network` loop):
1. `process_cmd(...)` polls `worker_io` for commands (`stop`/`remove`/`add`/
   `create`); returns `False` on `stop`.
2. `forward_data(selector, master_files, master_cache, slave_names, loopback, logger, data_logging_file, data_logging_splitter)`:
   - `selector.select(timeout=1)` yields readable master fds.
   - `data = master_files[fd].read()`.
   - if data logging enabled: append to `master_cache[fd]`, split on
     `data_logging_splitter`, write hex+repr lines to a rotating log.
   - for every other master fd (or all, if `loopback`): `f.write(data)`.
3. Loop repeats until `process_cmd` returns `False`.

**Destination**: all other ports in the network (broadcast), or all ports
including sender when `loopback=True`.

**Transformations**: raw bytes; optional hex/str logging with splitter-based
framing.

**Boundaries**: separate `multiprocessing.Process`; `selectors` event loop with
1s timeout; `Pipe` for control messages.

---

## Flow 6 — Virtual network control (parent ↔ worker)

**Source**: parent calls `VirtualSerialNetwork.start/add/create/remove/stop`.

**Path**:
1. Parent sends a dict over `__master_io`:
   - `start`: process args carry initial config; worker sends one response per
     port created/added.
   - `add`: `{"cmd": "add", "payload": [<config dicts>]}`.
   - `create`: `{"cmd": "create", "payload": <int>}`.
   - `remove`: `{"cmd": "remove", "payload": [<port names>]}`.
   - `stop`: `{"cmd": "stop"}`.
2. Worker `process_cmd` dispatches to `generate_virtual_ports` /
   `add_external_ports` / `remove_ports`.
3. Worker replies `{"status": "OK"|"ERROR"|"EXIST"|"NOT_EXIST", "payload": ...}`
   per item.
4. Parent blocks on `__master_io.recv()` for the expected number of responses
   and updates `serial_ports`, `virtual_ports_num`, `external_ports`.

**Destination**: parent-side state (`serial_ports`, `virtual_ports_num`,
`external_ports`).

**Transformations**: config objects → `to_dict()` → dict over `Pipe` →
`serial.Serial(**dict)` for external ports.

**Boundaries**: `multiprocessing.Pipe`; synchronous request/response (parent
blocks on `recv`).

**Note (fact)**: `start()` reads exactly `virtual_ports_num` responses for
virtual ports and `len(external_ports)` responses for external ports. If the
worker sends a different count, the parent can block or desynchronize.

---

## Flow 7 — End-to-end Modbus over virtual pair (tests/examples)

**Source**: `RS485Client` call in a test/example.

**Path**:
1. `VirtualSerialPair.start()` creates two pty ports; `serial_ports[0]` and
   `[1]`.
2. `RS485Server(ModbusSerialConnectionConfig(serial_ports[0]))` starts on port 0.
3. `RS485Client(ModbusSerialConnectionConfig(serial_ports[1]), address=1)`.
4. Client request bytes → port 1 slave → worker reads master → forwards to port
   0 master → server reads → pymodbus decodes → datastore → response bytes →
   port 0 → worker forwards to port 1 → client reads response.

**Destination**: client receives the Modbus response.

**Transformations**: PDU → ADU (client framer) → bytes → (virtual forwarding) →
bytes → ADU → PDU (server framer) → datastore → response PDU → ADU → bytes →
(virtual forwarding) → bytes → ADU → PDU (client framer).

**Boundaries**: async client/server + separate worker process + OS pty.

---

## Flow 8 — Custom protocol (framer/decoder/PDU)

**Source**: `examples/rs485_custom_request.py` and
`tests/server/test_custom_request.py`.

**Path**:
1. Custom `FramerAscii` subclass overrides `decode`/`encode`/`handleFrame`
   (device id in first 3 bytes, LRC checksum).
2. Custom `DecodePDU` subclass overrides `lookupPduClass`/`decode`.
3. Custom `ModbusPDU` subclasses (`CustomizedRequest`,
   `CustomizedModbusResponse`) implement `encode`/`decode`; the request's
   `datastore_update` writes/reads the server context.
4. Injected via `RS485Server(custom_pdu=..., custom_framer=..., custom_decoder=...)`
   and `RS485Client(custom_framer=..., custom_decoder=..., custom_response=...)`.

**Destination**: custom response PDU returned to the client.

**Transformations**: custom ASCII frame ↔ PDU; LRC via
`utilities.checksum.lrc` (example) or pymodbus `compute_LRC` (test).

**Boundaries**: same async + virtual-pair boundaries as Flow 7.

---

## Async / process / queue summary

| Boundary | Mechanism | Where |
| --- | --- | --- |
| Client I/O | `async`/`await` over pymodbus | `client/rs485_client.py`, `utilities/modbus.py` |
| Server serving | `asyncio.Task` running `serve_forever` | `server/rs485_server.py` |
| Virtual worker | `multiprocessing.Process` | `virtual/virtual_serial_network.py` |
| Parent↔worker control | `multiprocessing.Pipe` (dict messages) | `virtual/virtual_serial_network.py`, `virtual/worker.py` |
| Worker I/O multiplexing | `selectors.DefaultSelector` (1s timeout) | `virtual/worker.py:forward_data` |
| Data logging | `RotatingFileHandler` (10 MB × 5) | `virtual/worker.py:setup_data_logging` |
| Signals | `signal.signal` (parent), `pthread_sigmask` (worker) | `virtual/virtual_serial_network.py`, `virtual/worker.py` |

There are **no queues** other than the `Pipe`; no threads in `src/` (tests use
`threading.Thread` to run the worker in-process for coverage).
