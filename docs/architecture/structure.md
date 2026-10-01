# Structure

## Repository layout

```
scietex.hal.serial/
├── src/scietex/hal/serial/        # package root (implicit namespace: scietex/, hal/)
│   ├── __init__.py                # public API re-exports (__all__)
│   ├── version.py                 # __version__ (dynamic version source)
│   ├── py.typed                   # PEP 561 marker
│   ├── config/                    # connection configuration
│   ├── virtual/                   # virtual serial network
│   ├── server/                    # Modbus/RS485 server
│   ├── client/                    # Modbus/RS485 client
│   ├── gateway/                   # serial↔TCP Modbus gateway
│   └── utilities/                 # helpers (modbus, numeric, checksum, finder, exceptions)
├── tests/                         # mirrors src/ module structure
│   ├── conftest.py                # shared fixtures
│   ├── config/  virtual/  server/  client/  utilities/  gateway/
│   └── test_version.py
├── examples/                      # runnable usage scripts (linted)
├── docs/architecture/             # this map
├── pyproject.toml                 # build, deps, extras, coverage config
├── pytest.ini                     # pytest config (pythonpath, timeout)
├── tox.ini                        # env_list: format, lint, type, py{310,312,314}
├── cspell.json                    # project word list
└── .github/workflows/             # python-package.yml, python-lint.yml, python-publish.yml
```

## Namespace-package boundary

`src/scietex/` and `src/scietex/hal/` contain **no `__init__.py`** — they are
implicit namespace packages. The first real package is
`src/scietex/hal/serial/`. Do not add `__init__.py` above it.

## Module responsibilities

### `config/`

| Module | Responsibility |
| --- | --- |
| `serial_connection_interface.py` | ABCs: `SerialConnectionMinimalConfigModel`, `SerialConnectionConfigModel`, `ModbusSerialConnectionConfigModel` (abstract properties + `to_dict`) |
| `serial_connection_implementation.py` | Concrete classes: `SerialConnectionMinimalConfig`, `SerialConnectionConfig`, `ModbusSerialConnectionConfig`; validation on every setter; `to_dict`/`__str__`/`__repr__` |
| `validation.py` | `validate_port/baudrate/bytesize/parity/stopbits/timeout/framer`; raise `SerialConnectionConfigError` |
| `defaults.py` | Default values and allowed-value tuples (`DEFAULT_BAUDRATE_LIST`, etc.) |
| `exceptions.py` | `SerialConnectionConfigError(ValueError)` |
| `__init__.py` | Re-exports the three concrete configs + ABCs + exception |

### `virtual/`

| Module | Responsibility |
| --- | --- |
| `virtual_serial_network.py` | `VirtualSerialNetwork`: parent-side lifecycle (`start`/`stop`/`add`/`create`/`remove`), owns `Process` + `Pipe`, tracks `serial_ports`/`virtual_ports_num`/`external_ports` |
| `virtual_serial_pair.py` | `VirtualSerialPair(VirtualSerialNetwork)`: fixed 2-port specialization; disables `add`/`create`/`remove` |
| `worker.py` | Worker-process functions: `create_serial_network` (entry), `generate_virtual_ports`, `add_external_ports`, `remove_ports`, `forward_data`, `process_cmd`, `setup_data_logging` |
| `__init__.py` | Re-exports `VirtualSerialNetwork`, `VirtualSerialPair` |

### `server/`

| Module | Responsibility |
| --- | --- |
| `rs485_server.py` | `RS485Server`: wraps pymodbus `ModbusSerialServer`; device context management; `SERVER_INFO` identity dict |
| `modbus_datablock.py` | `ReactiveSequentialDataBlock(ModbusSequentialDataBlock)`: `setValues` override + `on_change` hook |
| `__init__.py` | Re-exports `RS485Server`, `ReactiveSequentialDataBlock` |

### `client/`

| Module | Responsibility |
| --- | --- |
| `rs485_client.py` | `RS485Client`: async typed register API over pymodbus; signed/float/32-bit helpers; `read_data`/`process_message` extension hooks |
| `__init__.py` | Re-exports `RS485Client` |

### `utilities/`

| Module | Responsibility |
| --- | --- |
| `modbus.py` | `modbus_connection_config`, `modbus_connection`, `modbus_get_client`, `modbus_execute`, `modbus_read_registers`, `modbus_read_input_registers`, `modbus_read_holding_registers`, `modbus_write_registers`, `modbus_write_register` |
| `numeric.py` | `ByteOrder` enum; signed/unsigned 16/32-bit conversions; float scaling; `split_32bit`/`combine_32bit` |
| `checksum.py` | `check_sum` (CRC-16/Modbus), `lrc`, `check_lrc` |
| `serial_port_finder.py` | `find_serial_ports`, `find_stm32_cdc`, `find_rs485`; `DEVICE_PROFILES` registry |
| `exceptions.py` | `ModbusOperationError` |
| `__init__.py` | Re-exports the stable public helpers (`__all__`) |

### `gateway/`

| Module | Responsibility |
| --- | --- |
| `config.py` | `GatewayConfig`, `GatewayDeviceConfig`; validation in `__post_init__`; fail-fast plugin resolvability checks |
| `exceptions.py` | `GatewayConfigError(ValueError)`, `GatewayError(Exception)` |
| `plugin_loader.py` | `load_class`, `resolve_framer`, `resolve_decoder`, `resolve_pdu`, `resolve_translator`, `build_framer` |
| `translator.py` | `GatewayTranslator` protocol (`to_vendor`/`to_standard`) for non-Modbus vendor protocols |
| `tcp_server.py` | `GatewayTcpServer`: custom asyncio Modbus/TCP front end using `FramerSocket` |
| `gateway.py` | `ModbusGateway`: forwarding core; owns the serial bus, routes by device id, swaps the framer per device |
| `__init__.py` | Re-exports the gateway config/exception/server/translator symbols |

## Boundaries between components

- **`config` ↔ everything**: `config` is imported by `virtual`, `server`,
  `client`, `gateway`, `utilities.modbus`. Nothing in `config` imports those
  modules.
- **`virtual` ↔ Modbus stack**: no import edge in either direction. They meet
  only at runtime through OS pseudo-terminal device paths (`serial_ports`).
- **`client` ↔ `server`**: no import edge. They meet at runtime over a serial
  port (real or virtual).
- **`gateway` ↔ endpoints**: `gateway` depends on `config` and pymodbus; it does
  not import `client`/`server`/`virtual`. It is a standalone protocol endpoint.
- **`utilities` ↔ endpoints**: `client` and `server` import `utilities.modbus`;
  `client` also imports `utilities.numeric`. `utilities.modbus` imports `config`.
- **`utilities` internal**: `numeric`, `checksum`, `serial_port_finder`,
  `exceptions` are leaves; `modbus` depends on `config`.

## Test structure

`tests/` mirrors `src/`:

| Test dir | Covers |
| --- | --- |
| `tests/config/` | minimal/serial/modbus config implementations + validation |
| `tests/virtual/` | `VirtualSerialPair`, `VirtualSerialNetwork`, `create_serial_network` worker |
| `tests/server/` | `RS485Server` lifecycle + custom framer/decoder/PDU |
| `tests/client/` | `RS485Client` read/write paths |
| `tests/utilities/` | checksum, numeric, modbus helpers |
| `tests/gateway/` | gateway config, forwarding core, plugin loader, TCP server, translator end-to-end |
| `tests/test_version.py` | version string format |

`tests/conftest.py` provides `logger_fixture`, `store_fixture`,
`single_slave_fixture`, `vsp_fixture`, `vsn_fixture`, `server_config`,
`client_config`, `rs485_srv`.

## Configuration files

- `pyproject.toml` — build (setuptools), deps, extras (`all`/`dev`/`test`/`lint`),
  dynamic version, `[tool.coverage.run]` (multiprocessing + parallel).
- `pytest.ini` — `pythonpath = .`, `addopts = --capture=no`,
  `asyncio_default_fixture_loop_scope = session`, `timeout = 10`,
  `timeout_method = signal`.
- `tox.ini` — `env_list = format, lint, type, py{310,312,314}`: `format` (ruff
  format), `lint` (ruff check), `type` (ty check src), `py{...}` (coverage +
  pytest).
- `cspell.json` — spellcheck word list.
- `.github/workflows/` — `python-package.yml` (pytest, matrix 3.10/3.12/3.14),
  `python-lint.yml` (ruff check), `python-publish.yml` (PyPI on release).
