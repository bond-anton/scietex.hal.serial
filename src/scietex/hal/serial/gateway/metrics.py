"""
Gateway telemetry counters.

`GatewayMetrics` accumulates the counters a running `ModbusGateway` exposes for
telemetry: total forwarded requests, gateway-level failures, observed bus
retries, and per-device request/error/last-seen state. The counters are plain
in-process integers guarded by no lock: the gateway serializes all bus access
through a single `asyncio.Lock`, so every mutation happens on one task at a
time and reads are best-effort snapshots.

The counters are deliberately transport-agnostic and free of any wire format;
the service layer snapshots them into its own telemetry struct.
"""

import time
from dataclasses import dataclass, field


@dataclass
class DeviceCounters:
    """
    Per-device request counters.

    Attributes:
        requests (int): Requests forwarded to this device.
        errors (int): Requests that failed with a gateway-level error (0x0B).
        last_seen (float | None): Monotonic timestamp of the last request, or
            None if the device has never been addressed.
    """

    requests: int = 0
    errors: int = 0
    last_seen: float | None = None


@dataclass
class GatewayMetrics:
    """
    Aggregate gateway counters.

    Attributes:
        requests (int): Total requests forwarded to the bus.
        errors (int): Total requests that failed with a gateway-level error.
        retries (int): Bus retries observed on returned responses. A request
            that exhausts its retries raises before returning a response, so
            those retries are not observable here.
        devices (dict[int, DeviceCounters]): Per-device counters, keyed by
            device id.
    """

    requests: int = 0
    errors: int = 0
    retries: int = 0
    devices: dict[int, DeviceCounters] = field(default_factory=dict)

    def record_request(self, device_id: int) -> None:
        """Count one forwarded request for a device."""
        self.requests += 1
        self._device(device_id).requests += 1

    def record_error(self, device_id: int) -> None:
        """Count one gateway-level failure for a device."""
        self.errors += 1
        self._device(device_id).errors += 1

    def record_retries(self, device_id: int, retries: int) -> None:
        """Add the retries observed on a returned response."""
        if retries > 0:
            self.retries += retries

    def touch(self, device_id: int) -> None:
        """Stamp the last-seen time for a device."""
        self._device(device_id).last_seen = time.monotonic()

    def _device(self, device_id: int) -> DeviceCounters:
        counters = self.devices.get(device_id)
        if counters is None:
            counters = DeviceCounters()
            self.devices[device_id] = counters
        return counters
