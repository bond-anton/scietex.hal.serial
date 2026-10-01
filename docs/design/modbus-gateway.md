# Design — Modbus Gateway

Status: **implemented** (released in 2.0.0)
Last updated: 2026-10-01

A serial↔TCP Modbus gateway for `scietex.hal.serial`. This document records the
settled design and the verified technical facts behind the implementation.

This document covers **Modbus devices** (RTU/ASCII framing differences only).
For devices that speak a **non-Modbus vendor protocol**, see the companion
document `modbus-gateway-nonstandard.md` (translator-PDU path).

## Goal

A gateway that owns one physical serial port (RS485 bus) and routes Modbus
requests between TCP/IP clients and the physical devices on that bus, **by
device id**. Clients connect with standard Modbus/TCP — no special protocol, no
control channel. The gateway decodes/encodes both ways with the correct framers,
selecting framer/decoder/PDU per device from configuration.

## Settled decisions

| Aspect | Decision |
| --- | --- |
| Transport | **TCP/IP only** (no virtual serial pairs) |
| Architecture | **Frame-level proxy** — the gateway forwards to the bus; it does not answer from a datastore |
| Gateway class | **Library class** `ModbusGateway(config, logger=None)` with `start()`/`stop()`, consistent with `RS485Server`/`RS485Client` |
| Config input | A **dataclass passed as an argument** — no file I/O, no config-dir, no ENV handling in this package |
| Config provisioning | **Out of scope** — a future separate service project (built on `scietex.service`) owns config files, config-dir resolution, and ENV overrides |
| Dependencies | **Unchanged** — still only `pymodbus[serial] ~= 3.15` (no `pyyaml`/`msgspec`) |
| Plugin mechanism | **Dotted-path strings** in the config dataclass (e.g. `"mypackage.MyFramer"`), resolved by a loader |
| Non-standard devices | **Translator PDU** — a plugin `GatewayTranslator` maps standard Modbus ↔ vendor protocol; see `modbus-gateway-nonstandard.md` |
| Built-in framers | `"RTU"`, `"ASCII"` shortcuts (uppercase, matching `FramerType` and `ModbusSerialConnectionConfig.framer`); `"SOCKET"`/`"TLS"` excluded (serial bus) |
| Default framer | `default_framer: "RTU" \| "ASCII"` field on the config dataclass |
| Framer swap | **Smart** — swap only when the target framer differs from the currently-installed one; no restore-to-default after each request |
| Concurrency | One `asyncio.Lock` around swap+execute (the bus is one physical line) |
| Unknown device id | `allow_unknown_devices` flag; default `False` → reject with exception 0x0B |
| Bus failure | Modbus exception response (0x0B), TCP connection stays open |

## Architecture

```
TCP client ──Modbus/TCP──▶ GatewayTcpServer ──▶ ModbusGateway ──▶ AsyncModbusSerialClient ──▶ RS485 bus
             (FramerSocket)   decode→PDU        lock + framer swap      (per-device framer)
```

Two independent framer layers:

| Layer | Framer | Who chooses |
| --- | --- | --- |
| Client ↔ gateway (TCP) | `FramerSocket` (standard MBAP) | fixed, standard |
| Gateway ↔ bus (serial) | RTU / ASCII / custom | **the config, per device id** |

## Verified technical facts (pymodbus 3.15.0)

Confirmed against the installed package; treat as ground truth.

- `FramerType` has only 4 members: `ASCII`, `RTU`, `SOCKET`, `TLS`.
  `FRAMER_NAME_TO_CLASS` maps them to `FramerAscii`, `FramerRTU`, `FramerSocket`,
  `FramerTLS`. There is **no** `ModbusSocketFramer`/`ModbusRtuFramer` (2.x names)
  and **no** `RTU_OVER_TCP` enum member.
- `FramerBase` interface: `decode(self, data: bytes) -> tuple[int, int, int, bytes]`
  returning `(used_len, dev_id, tid, pdu_bytes)`; `encode(self, payload: bytes,
  dev_id: int, tid: int) -> bytes`; plus `buildFrame`/`handleFrame`. Class attrs
  `EMPTY`, `MIN_SIZE`. Constructor takes a `DecodePDU`.
- `FramerSocket.decode`/`encode` are **pure functions** with no transport
  coupling — usable standalone in a custom asyncio TCP server. Verified
  round-trip: TCP frame → `DecodePDU(True).decode` → PDU object → `client.execute`
  → response PDU → `.encode()` → `FramerSocket.encode` → TCP frame.
- `AsyncModbusSerialClient.ctx` is a `TransactionManager`; `client.ctx.framer` is
  a plain attribute read **fresh** on every send and receive
  (`TransactionManager.send`/`_recv`/`execute`) — never cached. Runtime swap is
  safe. The repo already replaces `client.ctx` wholesale in `modbus_get_client`
  (`utilities/modbus.py`).
- `client.execute(no_response_expected: bool, request: ModbusPDU)` returns the
  response PDU.
- `ModbusTcpServer`/`ModbusSerialServer` answer from a datastore and have **no
  forwarding hook**. pymodbus removed its old forwarder (`RemoteDeviceContext`,
  removed in 3.13.0: "a proper forwarder should be made at frame level"). Hence
  the custom TCP server.
- `ModbusSerialServer` and `AsyncModbusSerialClient` **cannot share one serial
  port** in one process (exclusive fd). The gateway owns the port via the client
  only.
- `ModbusServerContext`/`ModbusDeviceContext` are deprecated in 3.15 (v4
  removal); the gateway needs no server context at all.
- `AsyncModbusTcpClient(host, *, framer=FramerType.SOCKET, port=502, ...)`;
  per-request unit id is `device_id=` (NOT `slave=`).

### Spike result (PASS)

A time-boxed spike proved the core mechanism end-to-end over a real pty pair:
swapping `client.ctx.framer` between RTU and ASCII on a live client works when
the client framer matches the device/server framer. A framer **mismatch**
correctly yields a bus timeout (→ exception response), which is the behavior a
gateway needs. This de-risks the highest-risk part of the design.

## Structure

New package `src/scietex/hal/serial/gateway/` (mirrors `server/`/`client/`):

| File | Responsibility |
| --- | --- |
| `exceptions.py` | `GatewayConfigError`, `GatewayError` |
| `plugin_loader.py` | `resolve_framer`/`resolve_decoder`/`resolve_pdu`/`resolve_translator`/`build_framer`/`load_class` |
| `config.py` | `GatewayConfig`, `GatewayDeviceConfig` — **dataclasses only**, no file I/O |
| `translator.py` | `GatewayTranslator` protocol — standard Modbus ↔ vendor protocol mapping (see `modbus-gateway-nonstandard.md`) |
| `tcp_server.py` | `GatewayTcpServer` — asyncio server, `FramerSocket` decode, per-connection buffering |
| `gateway.py` | `ModbusGateway` — bus ownership, framer cache, smart swap, lock, translator dispatch, error mapping |

## Config dataclasses

Constructed in code (by the future service), not parsed from a file:

```python
@dataclass(slots=True)
class GatewayDeviceConfig:
    device_id: int
    framer: str = "RTU"  # "RTU" | "ASCII" | dotted path
    decoder: str | None = None  # dotted path
    pdus: list[str] = field(default_factory=list)  # dotted paths
    translator: str | None = None  # dotted path to GatewayTranslator; None = pass-through


@dataclass(slots=True)
class GatewayConfig:
    serial: ModbusSerialConnectionConfig  # reuse existing config model
    host: str = "0.0.0.0"
    port: int = 502
    default_framer: str = "RTU"  # "RTU" | "ASCII"
    devices: dict[int, GatewayDeviceConfig] = field(default_factory=dict)
    allow_unknown_devices: bool = False
    bus_retries: int = 0
```

Validation runs in `__post_init__` (device id range 1..247, framer resolvability,
duplicate ids, port range 1..65535) — raising `GatewayConfigError`. No
`from_dict`/`load`/`to_dict`.

Open item: whether `serial` reuses `ModbusSerialConnectionConfig` (DRY, but its
`framer` field is redundant with `default_framer`) or a dedicated gateway serial
config. Lean: reuse it, document that `default_framer` wins.

## Smart framer swap

```python
async def _on_request(self, dev_id, tid, request):
    async with self._lock:
        target = self._framer_for(dev_id)  # cached FramerBase instance
        if self._current_framer is not target:  # only swap when different
            self._bus.ctx.framer = target
            self._current_framer = target
        response = await self._bus.execute(False, request)
    return response
```

- All-RTU devices → **zero swaps after the first request**.
- No restore-to-default after each request — the last-used framer stays installed.
- Swap only on a genuine framer change.

## TCP server

Custom asyncio server (NOT `ModbusTcpServer`). Per connection:

```python
decoder = DecodePDU(True)
for pdu_cls in self._request_pdus:  # union of custom request PDUs from config
    decoder.register(pdu_cls)
framer = FramerSocket(decoder)  # per connection (no state bleed)
buffer = b""
while chunk := await reader.read(4096):
    buffer += chunk
    while buffer:
        used, dev_id, tid, pdu_bytes = framer.decode(buffer)
        if used == 0:  # incomplete -> wait for more
            break
        buffer = buffer[used:]
        await self._dispatch(writer, dev_id, tid, pdu_bytes)
```

Response framing (pymodbus `ModbusPDU.encode()` returns **data only**; the
function code is prefixed by the framer):

```python
payload = pdu.function_code.to_bytes(1, "big") + pdu.encode()
frame = FramerSocket.encode(payload, dev_id, tid)  # echoes the client's TID
```

## Phased delivery

Each phase is a separate PR. **Gate per phase:** `ruff format --check` →
`ruff check` → `ty check src` → `tox -e py314`.

1. **Plugin loader + exceptions** — dotted-path resolution, built-in `"RTU"`/`"ASCII"`,
   `resolve_translator`. ✅ done
2. **Config dataclasses + validation** — no file I/O; `translator` field. ✅ done
3. **Forwarding core** (`ModbusGateway`, no TCP yet) — spike already passed; smart
   swap, lock, broadcast, translator dispatch, error mapping. ✅ done
4. **TCP server + end-to-end wiring** — `GatewayTcpServer`, real
   `AsyncModbusTcpClient` ↔ gateway ↔ pty ↔ `RS485Server` tests. ✅ done
5. **Public API + full gate** — export from `scietex.hal.serial`, run full `tox`. ✅ done

Non-standard (vendor-protocol) devices are covered by
`modbus-gateway-nonstandard.md`, which extends phases 1–5 above.

## Testing (no hardware)

Reuse the existing `VirtualSerialPair` + `RS485Server` fixtures: the gateway
binds one pty end, a real server the other, a real `AsyncModbusTcpClient` drives
it. Covers: routing by device id, per-device framer switching, unknown-id policy,
broadcast, bus timeout → exception, concurrent clients, custom framer/PDU via
config, partial/coalesced TCP frames, lifecycle.

## Risks & open items

1. **Framer swap concurrency** — mitigated by the lock; **spike passed**, so
   de-risked.
2. **Partial/coalesced TCP frames** — `FramerSocket.decode` returns `used==0` for
   incomplete frames; a per-connection max-buffer guard (`_MAX_BUFFER`, 64 KiB)
   drops a connection that never completes a frame.
3. **TID echo** — `TransactionManager` overwrites the request TID; the TCP TID
   must be captured server-side and echoed.
4. **Custom decoder contract** — must accept a single positional `is_server: bool`;
   no extra-args support (YAGNI).
5. **`serial.framer` vs `default_framer`** — two sources of truth; `default_framer`
   wins, documented.
6. **`allow_unknown_devices` default** — set to `False` (safer); confirm.
7. **`serial` field type** — reuse `ModbusSerialConnectionConfig` vs dedicated
   config; lean reuse.

## Out of scope (future service project)

- Config file format (YAML/JSON/TOML) and parsing.
- Config-directory resolution (`/etc/scietex`, `~/.config/scietex`,
  `SCIETEX_CONFIG_DIR`) — `scietex.service.prepare_conf_dir()` is the reusable
  helper there.
- ENV overrides.
- Daemon lifecycle, signal handling, logging — `scietex.service.BasicWorker`.
- CLI entry point, README usage example.
