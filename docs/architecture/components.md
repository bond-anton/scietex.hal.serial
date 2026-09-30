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
- `modbus_get_client(con_params, custom_framer=None, custom_decoder=None, custom_response=None, label=None) -> AsyncModbusSerialClient` — builds client and
  installs a `TransactionManager` with `retries=3`.
- `modbus_execute(client, request, no_response_expected=False, logger=None)`
- `modbus_read_registers(client, start_register=0, count=1, device_id=1, holding=True, max_count=0, logger=None)`
- `modbus_read_input_registers(...)`, `modbus_read_holding_registers(...)` —
  wrappers over `modbus_read_registers`.
- `modbus_write_registers(client, register, value, device_id=1, max_count=0, logger=None, no_response_expected=False)`
- `modbus_write_register(client, register, value, device_id=1, logger=None, no_response_expected=False)`

**Depends on**: `config` (`SerialConnectionMinimalConfigModel`),
`config.defaults` (`DEFAULT_TIMEOUT`, `DEFAULT_FRAMER`); `pymodbus`.

**Depended on by**: `client`, `server`.

**Notes**: every function calls `client.connect()` and `client.close()` around
the operation. `modbus_read_registers`/`modbus_write_registers` implement
chunking via `max_count`.

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

### 5e. `mock.py`

**Purpose**: Test double for pty creation failure.

**Main function**: `mock_openpty()` — always raises `OSError`.

**Depends on**: nothing. **Depended on by**: tests.

---

## 6. Package root (`__init__.py`)

**Purpose**: Public API surface.

**Re-exports** (`__all__`): `__version__`, `SerialConnectionMinimalConfig`,
`SerialConnectionConfig`, `ModbusSerialConnectionConfig`,
`VirtualSerialNetwork`, `VirtualSerialPair`, `RS485Client`, `RS485Server`,
`ReactiveSequentialDataBlock`.

**Depends on**: `version`, `config`, `virtual`, `client`, `server`.

**Notes**: `utilities` is **not** re-exported at the root; consumers import
`utilities.*` submodules directly (as examples do).
