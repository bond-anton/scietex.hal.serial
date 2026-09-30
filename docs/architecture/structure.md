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
│   └── utilities/                 # helpers (modbus, numeric, checksum, finder, mock)
├── tests/                         # mirrors src/ module structure
│   ├── conftest.py                # shared fixtures
│   ├── config/  virtual/  server/  client/  utilities/
│   └── test_version.py
├── examples/                      # runnable usage scripts (linted)
├── docs/architecture/             # this map
├── pyproject.toml                 # build, deps, mypy, pytest config
├── pytest.ini                     # overrides pyproject pytest config
├── tox.ini                        # env_list: format, lint, type, py314
├── cspell.json                    # project word list
└── .github/workflows/             # python-package.yml, pylint.yml, python-publish.yml
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
| `modbus.py` | `modbus_connection_config`, `modbus_get_client`, `modbus_execute`, `modbus_read_registers`, `modbus_read_input_registers`, `modbus_read_holding_registers`, `modbus_write_registers`, `modbus_write_register` |
| `numeric.py` | `ByteOrder` enum; signed/unsigned 16/32-bit conversions; float scaling; `split_32bit`/`combine_32bit` |
| `checksum.py` | `check_sum` (CRC-16/Modbus), `lrc`, `check_lrc` |
| `serial_port_finder.py` | `find_serial_ports`, `find_stm32_cdc`, `find_rs485`; VID/PID constants |
| `mock.py` | `mock_openpty` (raises `OSError`) for error-path tests |
| `__init__.py` | Empty (no re-exports) |

## Boundaries between components

- **`config` ↔ everything**: `config` is imported by `virtual`, `server`,
  `client`, `utilities.modbus`. Nothing in `config` imports those modules.
- **`virtual` ↔ Modbus stack**: no import edge in either direction. They meet
  only at runtime through OS pseudo-terminal device paths (`serial_ports`).
- **`client` ↔ `server`**: no import edge. They meet at runtime over a serial
  port (real or virtual).
- **`utilities` ↔ endpoints**: `client` and `server` import `utilities.modbus`;
  `client` also imports `utilities.numeric`. `utilities.modbus` imports `config`.
- **`utilities` internal**: `numeric`, `checksum`, `mock`, `serial_port_finder`
  are leaves; `modbus` depends on `config`.

## Test structure

`tests/` mirrors `src/`:

| Test dir | Covers |
| --- | --- |
| `tests/config/` | minimal/serial/modbus config implementations + validation |
| `tests/virtual/` | `VirtualSerialPair`, `VirtualSerialNetwork`, `create_serial_network` worker |
| `tests/server/` | `RS485Server` lifecycle + custom framer/decoder/PDU |
| `tests/client/` | `RS485Client` read/write paths |
| `tests/utilities/` | checksum, numeric, modbus helpers |
| `tests/test_version.py` | version string format |

`tests/conftest.py` provides `logger_fixture`, `store_fixture`,
`single_slave_fixture`, `vsp_fixture`, `vsn_fixture`, `server_config`,
`client_config`, `rs485_srv`.

## Configuration files

- `pyproject.toml` — build (setuptools), deps, extras (`dev`/`test`/`lint`),
  dynamic version, `[tool.mypy] python_version = "3.10"`,
  `[tool.pytest.ini_options] pythonpath = ["src"]`.
- `pytest.ini` — `pythonpath = .`, `addopts = --capture=no`,
  `asyncio_default_fixture_loop_scope = session`, `timeout = 10`,
  `timeout_method = signal`. **Overrides** the pyproject pytest section.
- `tox.ini` — envs `format` (black), `lint` (pylint src tests examples),
  `type` (mypy src), `py{314}` (coverage + pytest).
- `cspell.json` — spellcheck word list.
- `.github/workflows/` — `python-package.yml` (flake8 + pytest, matrix
  3.10/3.12/3.14), `pylint.yml`, `python-publish.yml` (PyPI on release).
