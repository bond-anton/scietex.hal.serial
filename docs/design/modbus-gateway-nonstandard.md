# Design — Non-Standard Protocol Support Path

Status: **implemented** (released in 2.0.0)
Last updated: 2026-10-01

Extends `docs/design/modbus-gateway.md`. That document covers the frame-level
proxy for Modbus devices (RTU/ASCII framing differences only). This document
covers devices that speak a **non-Modbus vendor protocol** and must be reached
transparently by a standard Modbus/TCP client.

## Goal

A standard Modbus/TCP client sends a normal Modbus request (e.g. FC03 read
holding registers). The gateway translates it into a vendor command, sends it
over the serial bus, translates the vendor response back into a standard Modbus
response, and returns it to the client. The client never knows the device is
non-Modbus.

## Decision: translator PDU

The plugin supplies a **`ModbusPDU` subclass that is the translator**. It fits
pymodbus's existing pipeline unchanged — no new gateway abstraction. This reuses
the convention already proven in `scietex.hal.vacuum_gauge`
(`ThyracontRequest` + `ThyracontRS485ASCIIFramer` + `ThyracontRS485DecodePDU`).

### Why this fits the existing pipeline (verified, pymodbus 3.15.0)

```
execute() → pdu_send() → framer.buildFrame(pdu)
                              └─ function_code.to_bytes(1,"big") + pdu.encode()
                                 → framer.encode(payload, dev_id, tid)
```

The translator PDU controls **both** the function-code byte and the body via
`function_code` + `encode()`. The framer controls the wire envelope. Nothing
else in the pipeline needs to change.

## The translation boundary

The one genuinely new problem: a TCP client sends **standard** Modbus (FC03 @
addr 0), but the vendor device expects a **vendor** command (`"M"`). The gateway
must map standard→vendor and vendor→standard.

Resolution: the translator is constructed *from* the decoded standard request.
The gateway does not interpret vendor semantics; it delegates to a per-device
**translator** supplied by the plugin.

### Plugin contract (new)

```python
class GatewayTranslator(Protocol):
    """Maps standard Modbus PDUs to/from a vendor protocol."""

    def to_vendor(self, request: ModbusPDU) -> ModbusPDU:
        """Standard request PDU -> vendor request PDU (its function_code/encode
        produce the vendor wire bytes)."""

    def to_standard(self, response: ModbusPDU) -> ModbusPDU:
        """Vendor response PDU -> standard response PDU returned to the TCP client."""
```

- `to_vendor` receives the decoded standard request (e.g.
  `ReadHoldingRegistersRequest`) and returns a vendor PDU (e.g.
  `ThyracontRequest(command="M")`).
- `to_standard` receives the decoded vendor response and returns a standard
  response PDU (e.g. `ReadHoldingRegistersResponse(registers=[...])`).
- Both are **pure** — no I/O. The gateway owns the bus.

### Placement

The `GatewayTranslator` interface lives in the gateway package (generic). Vendor
implementations live in separate plugin packages (e.g. `scietex.hal.vacuum_gauge`),
resolved by dotted path.

## Config wiring

`GatewayDeviceConfig` gains one field:

```python
@dataclass(slots=True)
class GatewayDeviceConfig:
    device_id: int
    framer: str = "RTU"  # "RTU" | "ASCII" | dotted path
    decoder: str | None = None  # dotted path
    pdus: list[str] = field(default_factory=list)  # vendor PDU classes to register
    translator: str | None = None  # dotted path to GatewayTranslator subclass
```

- `translator=None` → **pass-through** (frame-proxy behavior; device speaks
  Modbus).
- `translator="mypkg.MyTranslator"` → non-standard path.

## Request flow (non-standard device)

```
TCP client ──FC03 @ addr 0──▶ GatewayTcpServer
   decode FramerSocket → standard ReadHoldingRegistersRequest
        │
        ▼
   ModbusGateway._on_request(dev_id, tid, std_request)
        │  translator = self._translator_for(dev_id)
        │  vendor_req = translator.to_vendor(std_request)   # -> ThyracontRequest("M")
        │  vendor_req.dev_id = dev_id
        │
        ▼  async with lock: swap framer if needed
   bus.execute(False, vendor_req)   # framer.buildFrame -> vendor wire bytes
        │
        ▼  vendor response PDU (ThyracontRequest with .data)
   std_response = translator.to_standard(vendor_response)
        │
        ▼
   FramerSocket.encode(std_response) ──▶ TCP client
```

## Verified technical constraints (pymodbus 3.15.0)

1. **`dev_id` must be set at construction** — `execute()` overwrites
   `transaction_id` but never `dev_id` (`TransactionManager.execute`). The
   gateway sets `vendor_req.dev_id = dev_id` before `execute`.
2. **`transaction_id` is forced to 0** for ASCII/RTU framers
   (`TransactionManager.getNextTID`). The TCP TID must be captured server-side
   and echoed (already an open item in the base design).
3. **Response matching** — `FramerBase.handleFrame` filters by expected
   `dev_id`/`tid` and stamps the response PDU. The vendor framer's `decode()`
   must return `(used_len, dev_id, tid, frame_data)`.
4. **`execute` validates** `response.dev_id == request.dev_id` when
   `request.dev_id` is truthy (`TransactionManager.execute`). The vendor
   response must carry the same `dev_id`.
5. **`DecodePDU.register` maps a class as both request and response**
   (`DecodePDU.register`). Vendor PDUs registered via `pdus` must handle both
   directions, or the translator must supply distinct classes.
6. **`function_code` collision** — vendor PDUs use arbitrary function codes
   (e.g. ASCII `"M"` = 0x4D). The vendor `DecodePDU` must be a custom subclass
   (like `ThyracontRS485DecodePDU`) that bypasses the standard `pdu_table`
   lookup, otherwise standard FCs collide.

## Framer/decoder selection per device

The gateway already plans a per-device framer cache + smart swap. The
non-standard path extends this:

- **Framer** — vendor framer (e.g. `ThyracontASCIIFramer`) from `framer` dotted
  path.
- **Decoder** — vendor decoder from `decoder` dotted path; constructed with
  `is_server=False` (client side) and with vendor PDUs registered.
- **PDUs** — vendor PDU classes from `pdus`, registered on the decoder.

The gateway builds one `(framer, decoder)` pair per device config, cached,
swapped under the lock.

## What the plugin author writes

For a new vendor device, the plugin provides **four** artifacts (mirroring
`vacuum_gauge`):

| Artifact | Base class | Example |
| --- | --- | --- |
| Vendor PDU | `ModbusPDU` | `ThyracontRequest` |
| Vendor framer | `FramerBase` (or `FramerAscii`/`FramerRTU`) | `ThyracontRS485ASCIIFramer` |
| Vendor decoder | `DecodePDU` | `ThyracontRS485DecodePDU` |
| Translator | `GatewayTranslator` | `ThyracontTranslator` (new) |

The first three are **reusable as-is** from `vacuum_gauge`. Only the translator
is new — it encodes the standard↔vendor mapping.

## Open items

1. **Translator granularity** — one translator per device, or per device *type*
   shared across ids? Lean: per device config (dotted path), instances cached by
   path.
2. **Standard response construction** — `to_standard` must build a valid
   standard response PDU (correct `function_code`, `registers`/`bits`). Who
   validates the vendor response maps cleanly (e.g. count mismatch)? Lean:
   translator raises `GatewayError` → mapped to exception 0x0B.
3. **Error mapping** — vendor timeout/checksum failure → standard Modbus
   exception response. Reuse the base design's 0x0B mapping.
4. **`pdus` vs `translator`** — if a translator is present, are `pdus` still
   needed? Lean: `pdus` registers vendor PDUs on the decoder; `translator` is
   separate. Both may be needed.
5. **Broadcast (dev_id 0)** — vendor protocols may not support broadcast;
   translator decides.

## Phasing

Extends the base design's phases:

1. **Plugin loader + exceptions** — add `resolve_translator` / `load_class` for
   `GatewayTranslator`. ✅ done
2. **Config dataclasses + validation** — add `translator` field + validation. ✅ done
3. **Forwarding core** — add translator dispatch in `_on_request`; pass-through
   when `None`. ✅ done
4. **TCP server + end-to-end wiring** — verified with a **synthetic vendor
   plugin** in `tests/gateway/vendor_stub/` (PDU + framer + decoder +
   translator) and a `VendorEmulator` on the serial side. A real vendor package
   (`vacuum_gauge`) is deliberately *not* a dependency: it would couple the two
   repos and it is currently broken against pymodbus 3.15. ✅ done
5. **Public API + full gate** — export `GatewayTranslator` from
   `scietex.hal.serial`. ✅ done

### Verification note

The synthetic stub doubles as a worked example of the plugin contract. It is
resolved by dotted path (`tests.gateway.vendor_stub.*`) exactly as a real plugin
would be, so the test exercises the same resolution, framer-swap, translator
dispatch and error-mapping code paths as production.

`vacuum_gauge` readiness (investigated, not implemented): the v1 PDU/framer/
decoder are resolvable and work through the generic `buildFrame` path (the
command rides in `function_code`). The missing artifact is a
`ThyracontTranslator`; the emulator also needs a pymodbus 3.15 fix
(`ModbusDeviceContext.store` no longer exists). Both belong to the
`vacuum_gauge` repo, not this one.
