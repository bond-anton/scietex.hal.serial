# Components

For each major component: purpose, main symbols, public interface, dependencies
(outgoing), and dependents (incoming). "Public" = reachable via the package
`__init__` re-exports or documented in module docstrings.

---

## 1. Configuration (`config/`)

**Purpose**: Typed, validated serial connection configuration shared by all
other components.

**Main classes**

- `SerialConnectionMinimalConfigModel` (ABC) — abstract properties `port`,
  `baudrate`, `bytesize`, `parity`, `stopbits`; abstract `to_dict()`.
- `SerialConnectionConfigModel(SerialConnectionMinimalConfigModel)` (ABC) — adds
  abstract `timeout`, `write_timeout`, `inter_byte_timeout`.
- `ModbusSerialConnectionConfigModel(SerialConnectionMinimalConfigModel)` (ABC) —
  adds abstract `timeout`, `framer`.
- `SerialConnectionMinimalConfig` — concrete; validates in `__init__` and every
  setter; `to_dict()` returns 5 keys.
- `SerialConnectionConfig(SerialConnectionMinimalConfig, SerialConnectionConfigModel)`
  — adds timeout fields; `to_dict()` returns 8 keys.
- `ModbusSerialConnectionConfig(SerialConnectionMinimalConfig, ModbusSerialConnectionConfigModel)`
  — adds `framer` + `timeout`; `to_dict()` returns 7 keys.
- `SerialConnectionConfigError(ValueError)`.

**Main functions**: `validate_port`, `validate_baudrate`, `validate_bytesize`,
`validate_parity`, `validate_stopbits`, `validate_timeout`, `validate_framer`.

**Public interface**: the three concrete configs + ABCs + exception, re-exported
from `config/__init__.py` and (the three concrete ones) from the package root.

**Depends on**: standard library only (`abc`). No intra-package deps.

**Depended on by**: `virtual` (`SerialConnectionMinimalConfig`),
`server` (`SerialConnectionConfigModel`, `ModbusSerialConnectionConfigModel`),
`client` (same), `utilities.modbus` (`SerialConnectionMinimalConfigModel`,
`config.defaults`).

**Notes**: `to_dict()` output is the serialization contract used to pass configs
across the process boundary (`VirtualSerialNetwork.start`/`add` call
`con_params.to_dict()`).

---

## 2. Virtual serial network (`virtual/`)

**Purpose**: Create and manage pseudo-terminal serial ports and forward bytes
between them, in a separate process.

**Main classes**

- `VirtualSerialNetwork` — parent-side manager.
  - `__init__(virtual_ports_num=2, external_ports=None, loopback=False, logger=None, data_log_dir=None, data_logging_splitter=None)`
  - `start(openpty_func=None)`, `stop()`, `add(external_ports) -> list[str]`,
    `create(ports_num) -> list[str]`, `remove(remove_list) -> list[str]`
  - private: `__master_io`, `__worker_io` (`Connection`), `__p` (`Process`),
    `_signal_handler`, `_ext_ports_remove_duplicates`, `_update_ext_ports`
  - public attrs: `serial_ports`, `virtual_ports_num`, `external_ports`,
    `loopback`, `logger`, `data_log_dir`, `data_logging_file`,
    `data_logging_splitter`
- `VirtualSerialPair(VirtualSerialNetwork)` — fixed 2-port; overrides
  `start` (stops if <2 ports), and no-ops `add`/`create`/`remove`.

**Main functions** (`worker.py`, run in the child process)

- `create_serial_network(worker_io, ports_number=2, external_ports=None, loopback=False, openpty_func=pty.openpty, logger=None, data_logging_file=None, data_logging_splitter=None)` — worker entry point.
- `generate_virtual_ports(...)`, `add_external_ports(...)`,
  `remove_ports(...)`, `forward_data(...)`, `process_cmd(...)`,
  `setup_data_logging(...)`.

**Public interface**: `VirtualSerialNetwork`, `VirtualSerialPair` (package root
and `virtual/__init__.py`).

**Depends on**: `config` (`SerialConnectionMinimalConfig`); stdlib `pty`,
`multiprocessing` (`Pipe`, `Process`, `Connection`), `selectors`, `signal`,
`os`, `tty`, `logging`, `pathlib`; `pyserial` (`serial.Serial`) for external
ports.

**Depended on by**: tests and examples only. No `src/` module imports `virtual`.

**Notes**: `forward_data` broadcasts to all ports except the sender (or
including it when `loopback=True`). The worker blocks `SIGINT`/`SIGTERM` via
`signal.pthread_sigmask`.

---

## 3. Server (`server/`)

**Purpose**: Modbus serial (RS485) server with dynamic device contexts.

**Main classes**

- `RS485Server`
  - `__init__(con_params, devices=None, custom_pdu=None, custom_framer=None, custom_decoder=None, logger=None)`
  - `async start()`, `async stop()`, `async restart()`,
    `async update_slave(slave_id, store)`, `async remove_slave(slave_id)`
  - attrs: `devices` (`dict[int, ModbusDeviceContext]`), `context`
    (`ModbusServerContext`), `identity` (`ModbusDeviceIdentification`),
    `con_params`, `logger`, `_task` (`asyncio.Task | None`), `server`
    (`ModbusSerialServer | None`)
- `ReactiveSequentialDataBlock(ModbusSequentialDataBlock)`
  - `setValues(address, values)` → calls `super().setValues` then `on_change`
  - `on_change(address, values)` → default logs; override hook

**Module constant**: `SERVER_INFO` (vendor/product identity dict).

**Public interface**: `RS485Server`, `ReactiveSequentialDataBlock` (package root
and `server/__init__.py`).

**Depends on**: `config` (config models), `utilities.modbus`
(`modbus_connection_config`), `version` (`__version__`); `pymodbus`
(`ModbusSerialServer`, `ModbusServerContext`, `ModbusDeviceContext`,
`ModbusDeviceIdentification`, `ModbusPDU`, `DecodePDU`, `FramerBase`); `asyncio`.

**Depended on by**: tests and examples only.

**Notes**: `update_slave`/`remove_slave` rebuild `self.context` and call
`restart()` if `_task` is set. `start()` is a no-op if `self.server` is not
`None`.

---

## 4. Client (`client/`)

**Purpose**: Async Modbus serial client with typed register helpers.

**Main class**: `RS485Client`
- `__init__(con_params, address=1, label="RS485 Device", custom_framer=None, custom_decoder=None, custom_response=None, chunk_size=None, write_chunk_size=None, logger=None)`
- properties: `con_params` (setter rebuilds client), `label` (setter rebuilds
  client)
- `async execute(request, no_response_expected=False)`
- `async read_registers(start_register=0, count=1, holding=True, signed=False)`
- `async read_register(register, holding=True, signed=False)`
- `async write_registers(start_register, values, signed=False, no_response_expected=False)`
- `async write_register(register, value, signed=False, no_response_expected=False)`
- `async read_register_float(register, factor=100, signed=False, holding=True)`
- `async write_register_float(register, value, factor=100, signed=False, no_response_expected=False)`
- `async read_two_registers_int(start_register, holding=True, byteorder=LITTLE_ENDIAN, signed=False)`
- `async read_two_registers_float(start_register, factor=100, holding=True, byteorder=LITTLE_ENDIAN, signed=False)`
- `async write_two_registers(start_register, value, byteorder=LITTLE_ENDIAN, signed=False, no_response_expected=False)`
- `async write_two_registers_float(start_register, value, factor=100, byteorder=LITTLE_ENDIAN, signed=False, no_response_expected=False)`
- `async read_data()` / `async process_message(message)` — extension hooks
  (default: log / return `{}`)
- attrs: `client` (`AsyncModbusSerialClient`), `address`, `logger`; private
  `__read_chunk_size`, `__write_chunk_size`

**Public interface**: `RS485Client` (package root and `client/__init__.py`).

**Depends on**: `config` (config models), `utilities.modbus`
(`modbus_get_client`, `modbus_execute`, `modbus_read_registers`,
`modbus_write_registers`, `modbus_write_register`), `utilities.numeric`
(`ByteOrder`, signed/float/32-bit helpers); `pymodbus` (`ModbusPDU`,
`DecodePDU`, `FramerBase`, `AsyncModbusSerialClient`).

**Depended on by**: tests and examples only.

**Notes**: `write_*` methods fall back to a read-back when the write response is
empty and `no_response_expected=False`. `chunk_size`/`write_chunk_size` bound
register batch sizes.

---

## 5. Utilities (`utilities/`)

### 5a. `modbus.py`

**Purpose**: Translate configs to pymodbus parameters and wrap pymodbus client
I/O with connect/close and error handling.

**Main functions**

- `modbus_connection_config(con_params) -> dict` — validates type, fills
  `timeout`/`framer` defaults, maps `"RTU"`/`"ASCII"` to `FramerType`, returns
  the 7-key dict.
- `modbus_get_client(con_params, custom_framer=None, custom_decoder=None, custom_response=None, label=None, retries=3) -> AsyncModbusSerialClient` — builds client and
  installs a `TransactionManager` with the given `retries`.
- `modbus_connection(client)` — async context manager; connects once, keeps the
  connection open for the block, and closes it on exit (pair with
  `manage_connection=False` on the wrappers).
- `modbus_execute(client, request, no_response_expected=False, logger=None, raise_on_error=True, manage_connection=True)`
- `modbus_read_registers(client, start_register=0, count=1, device_id=1, holding=True, max_count=0, logger=None, raise_on_error=True, manage_connection=True)`
- `modbus_read_input_registers(...)`, `modbus_read_holding_registers(...)` —
  wrappers over `modbus_read_registers`.
- `modbus_write_registers(client, register, value, device_id=1, max_count=0, logger=None, no_response_expected=False, raise_on_error=True, manage_connection=True)`
- `modbus_write_register(client, register, value, device_id=1, logger=None, no_response_expected=False, raise_on_error=True, manage_connection=True)`

**Depends on**: `config` (`SerialConnectionMinimalConfigModel`),
`config.defaults` (`DEFAULT_TIMEOUT`, `DEFAULT_FRAMER`); `pymodbus`.

**Depended on by**: `client`, `server`.

**Notes**: each function calls `client.connect()` and `client.close()` around
the operation unless `manage_connection=False` (use `modbus_connection` for a
reused connection). `raise_on_error=True` (default) raises
`ModbusOperationError` on failure; `False` returns `None`.
`modbus_read_registers`/`modbus_write_registers` implement chunking via
`max_count`.

### 5b. `numeric.py`

**Purpose**: Numeric representation conversions for register payloads.

**Main symbols**: `ByteOrder` enum (`LITTLE_ENDIAN="le"`, `BIG_ENDIAN="be"`);
`to_signed16/32`, `from_signed16/32`, `float_to_int`, `float_to_int16/32`,
`float_to_unsigned16/32`, `float_from_int`, `float_from_unsigned16/32`,
`split_32bit`, `combine_32bit`.

**Depends on**: stdlib `enum` only. **Depended on by**: `client`.

### 5c. `checksum.py`

**Purpose**: CRC-16/Modbus and LRC checksums.

**Main functions**: `check_sum(payload) -> int`, `lrc(payload) -> int`,
`check_lrc(message) -> bool`.

**Depends on**: nothing. **Depended on by**: examples/tests (custom framer
example uses `lrc`); not imported by `src/` modules.

### 5d. `serial_port_finder.py`

**Purpose**: Discover serial ports by USB VID/PID.

**Main symbols**: `find_serial_ports(vid_pid_mapping)`, `find_stm32_cdc()`,
`find_rs485()`; constants `STM_VID`, `STM_PID`, `STM_CDC_DEVICES`,
`RS485_DEVICES`.

**Depends on**: `pyserial` (`serial.tools.list_ports`). **Depended on by**:
examples only.

### 5e. `exceptions.py`

**Purpose**: Library-level operation exception.

**Main symbol**: `ModbusOperationError` — raised on protocol/transport failures
(when `raise_on_error=True`).

**Depends on**: nothing. **Depended on by**: `utilities.modbus`, `client`.

---

## 6. Gateway (`gateway/`)

**Purpose**: Frame-level serial↔TCP Modbus proxy. Owns one serial bus, accepts
standard Modbus/TCP clients, and routes requests to devices by id, swapping the
serial framer per device. Non-Modbus vendor protocols are supported through a
`GatewayTranslator` plugin (dotted-path config).

**Main classes**

- `GatewayConfig` — top-level gateway config: `serial`
  (`ModbusSerialConnectionConfigModel`), `host`, `port`, `default_framer`,
  `devices` (`dict[int, GatewayDeviceConfig]`), `allow_unknown_devices`,
  `bus_retries`. Validates in `__post_init__` and raises `GatewayConfigError`.
- `GatewayDeviceConfig` — per-device routing entry: `device_id`, `framer`,
  `decoder`, `pdus`, `translator`. Validates plugin references at construction
  (fail-fast).
- `GatewayConfigError(ValueError)` / `GatewayError(Exception)` — config and
  runtime exceptions.
- `ModbusGateway` — forwarding core.
  - `async start()`, `async stop()`
  - `async handle_request(device_id, request) -> ModbusPDU` — transport-agnostic
    entry point; maps bus/device failures to a Modbus exception response
    (0x0B), never raises to the TCP server.
  - private: `_create_bus`, `_build_runtimes`, `_build_device_runtime`,
    `_runtime_for`, `_forward`; `asyncio.Lock` serializes bus access.
- `GatewayTcpServer` — custom asyncio Modbus/TCP front end.
  - `async start()`, `async stop()`
  - `_handle_connection` decodes frames with `FramerSocket`, dispatches via
    `ModbusGateway.handle_request`, and echoes the client transaction id.
- `GatewayTranslator` (Protocol, `@runtime_checkable`) — plugin contract with
  `to_vendor(request)` / `to_standard(response)`; pure (no I/O).

**Main functions** (`plugin_loader.py`): `load_class`, `resolve_framer`,
`resolve_decoder`, `resolve_pdu`, `resolve_translator`, `build_framer`.

**Public interface**: `ModbusGateway`, `GatewayConfig`, `GatewayDeviceConfig`,
`GatewayTcpServer`, `GatewayTranslator`, `GatewayError`, `GatewayConfigError`
(package root and `gateway/__init__.py`).

**Depends on**: `config` (`ModbusSerialConnectionConfigModel`); `pymodbus`
(`AsyncModbusSerialClient`, `FramerType`, `FRAMER_NAME_TO_CLASS`, `FramerBase`,
`DecodePDU`, `ModbusPDU`, `FramerSocket`, `TransactionManager`,
`ModbusException`); `asyncio`; stdlib `importlib`.

**Depended on by**: tests and examples only.

**Notes**: `ModbusGateway.handle_request` never raises for bus/device failures —
it returns an `ExceptionResponse(0x0B)` so the TCP connection stays open. The
framer is swapped only when the target device's framer differs from the
currently-installed one. `start()` also tolerates a missing serial port: a
failed initial connect logs a warning and the gateway reconnects on the next
request (`_ensure_connected`), so it stays up and recovers once the port is
available. A port lost after startup behaves the same way — the next request
returns 0x0B and the gateway reconnects when the port returns.

---

## 7. Package root (`__init__.py`)

**Purpose**: Public API surface.

**Re-exports** (`__all__`, 26 symbols): `__version__`,
`SerialConnectionMinimalConfig`, `SerialConnectionConfig`,
`ModbusSerialConnectionConfig`, `VirtualSerialNetwork`, `VirtualSerialPair`,
`RS485Client`, `RS485Server`, `ReactiveSequentialDataBlock`,
`GatewayConfig`, `GatewayDeviceConfig`, `GatewayConfigError`, `GatewayError`,
`GatewayTranslator`, `ModbusGateway`, `GatewayTcpServer`,
`check_sum`, `lrc`, `check_lrc`, `ByteOrder`, `combine_32bit`, `split_32bit`,
`modbus_get_client`, `modbus_connection`, `find_serial_ports`,
`ModbusOperationError`.

**Depends on**: `version`, `config`, `virtual`, `client`, `server`, `gateway`,
`utilities`.

**Notes**: `utilities` is re-exported at the root (the stable helpers plus
`ModbusOperationError`); consumers may also import `utilities.*` submodules
directly (as examples do).
