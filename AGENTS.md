# AGENTS.md

Serial/Modbus communication library (`scietex.hal.serial`). Python, `src/` layout,
namespace package. Linux/macOS only — the virtual serial layer uses `pty.openpty`
and `multiprocessing`, so it does not run on Windows.

## Commands

Dependencies are managed with **uv**; tests and checks run through **tox**:

```bash
uv sync --all-extras          # create/refresh .venv with all extras
uv run tox                    # full env_list: format, lint, type, py{310,312,314}
uv run tox -e py314           # tests only (coverage run -m pytest tests)
uv run tox -e lint            # ruff check --fix src tests examples
uv run tox -e type            # ty check src
uv run tox -e format          # ruff format .
```

Single test / focused run — pass args through tox:

```bash
uv run tox -e py314 -- tests/virtual/test_virtual_serial_pair.py
uv run tox -e py314 -- tests/virtual/test_virtual_serial_pair.py::test_communication
```

To run pytest directly, install the test extra first:
`uv sync --extra test` then `uv run pytest`.

## Test setup (non-obvious)

- `pytest.ini` sets `pythonpath = .` and `addopts = --capture=no`; it **overrides**
  the `[tool.pytest.ini_options] pythonpath = ["src"]` in `pyproject.toml`.
- Tests use a dual-import shim because of the namespace layout:
  `try: from src.scietex... except ModuleNotFoundError: from scietex...`.
  Follow this pattern in new test files.
- `pytest-timeout` is configured with `timeout = 10` and `timeout_method = signal`
  (Unix-only). Tests that spawn the virtual-serial worker subprocess must finish
  within 10s.
- Tests run under `pytest-xdist` (`-n auto` in tox and CI). Keep tests
  **independent**: do not stop/restart shared fixtures (`vsp_fixture`,
  `rs485_srv`) mid-test — split into separate tests instead, or the pty port
  races under parallel load.
- Coverage uses `concurrency = ["multiprocessing"]` + `parallel = true`
  (`[tool.coverage.run]` in `pyproject.toml`) with `COVERAGE_PROCESS_START` set
  by tox, so xdist worker subprocesses are measured; `coverage combine` merges
  the per-process data files.
- Fixtures live in `tests/conftest.py` (`vsp_fixture`, `vsn_fixture`,
  `server_config`, `client_config`, `rs485_srv`, `store_fixture`). Reuse them
  instead of hand-rolling virtual ports.
- `tests/` mirrors `src/` module structure (`tests/config`, `tests/virtual`,
  `tests/server`, `tests/client`, `tests/utilities`).

## Architecture

- `src/scietex/hal/serial/` is the package root; `scietex/` and `hal/` are
  **implicit namespace packages** (no `__init__.py`). Do not add `__init__.py`
  there.
- Four modules: `config` (dataclass connection configs + validation),
  `virtual` (virtual serial networks), `server` (Modbus/RS485 server),
  `client` (Modbus/RS485 client). `utilities/` holds checksum, numeric, modbus
  helpers and test mocks.
- Public API is re-exported from `src/scietex/hal/serial/__init__.py`; add new
  public classes to its `__all__`.
- `virtual/` runs the port-forwarding loop in a **separate `multiprocessing`
  process** (`worker.py:create_serial_network`), driven over a `Pipe`. The
  parent (`virtual_serial_network.py`) sends `create`/`add`/`remove`/`stop`
  commands. The worker blocks SIGINT/SIGTERM so the parent controls shutdown.
- Version is dynamic: `pyproject.toml` reads `scietex.hal.serial.version.__version__`
  from `src/scietex/hal/serial/version.py`. Bump it there, not in `pyproject.toml`.

## Conventions

- `ruff` formatting and linting (`E`, `F`, `I`, `UP`; line length 100) on
  `src tests examples`; `ty` type checking on `src` only.
- `py.typed` is shipped — keep type annotations accurate.
- `cspell.json` maintains the project word list; add new domain terms there.
- `examples/` are runnable scripts (`if __name__ == "__main__":`), also linted.

## Known inconsistencies (verify before trusting)

- `pytest.ini` is the sole `pythonpath` source (`pythonpath = .`); `pyproject.toml`
  has no `[tool.pytest.ini_options]` section.
- `tox.ini` env_list targets `py{310,312,314}`, matching the CI matrix and
  `requires-python = ">=3.10"`.
- `uv.lock` is git-ignored (matching the sibling `scietex.*` repos); regenerate it
  with `uv lock` after changing dependencies.
