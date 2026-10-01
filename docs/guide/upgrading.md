# Upgrading to 2.0

Version 2.0 makes the error contract strict by default. Read, write, and execute
operations now raise `ModbusOperationError` on failure instead of returning
`None`.

```python
from scietex.hal.serial import ModbusOperationError

try:
    value = await client.read_register(0)
except ModbusOperationError as exc:
    print(f"Read failed: {exc}")
```

## What changed

- **Opt out per call.** Pass `raise_on_error=False` to restore the 1.x behavior
  of returning `None` on failure. The parameter exists on every read/write
  wrapper and `RS485Client` method, so you can migrate incrementally.
- **`None` is no longer a failure sentinel.** Stop using `if result is None` to
  detect failure; catch `ModbusOperationError` instead. `None` now only means
  "no response was expected" (`no_response_expected=True`).
- **Write→read fallback is opt-in.** In 1.x, a write whose response was falsy
  silently fell back to a read-back. That fallback now runs only when you pass
  `raise_on_error=False`. Devices that do not echo write responses must use
  `raise_on_error=False`; under that mode a `None` result means "unverifiable",
  not necessarily "failed".
- **`no_response_expected=True` is unchanged.** It still returns `None` and
  never raises.
- **Subclass authors.** Overrides of `read_data`/`process_message` that call
  `read_*` methods will now propagate `ModbusOperationError` unless each inner
  call passes `raise_on_error=False`.

## New in 2.0

- **Modbus Gateway.** A serial↔TCP gateway with per-device routing and support
  for non-Modbus vendor protocols. See the [Gateway guide](gateway.md).
