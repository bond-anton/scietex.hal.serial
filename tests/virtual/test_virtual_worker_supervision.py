"""Test virtual serial network worker supervision."""

import os
import signal

import pytest

try:
    from src.scietex.hal.serial.virtual import VirtualSerialNetwork
    from src.scietex.hal.serial.virtual.exceptions import VirtualSerialNetworkError
except ModuleNotFoundError:
    from scietex.hal.serial.virtual import VirtualSerialNetwork
    from scietex.hal.serial.virtual.exceptions import VirtualSerialNetworkError


def test_worker_death_raises_virtual_serial_network_error(logger_fixture):
    """A dead worker makes the next command raise VirtualSerialNetworkError."""
    vsn = VirtualSerialNetwork(virtual_ports_num=2, logger=logger_fixture)
    vsn.start()
    try:
        os.kill(vsn._VirtualSerialNetwork__p.pid, signal.SIGKILL)
        vsn._VirtualSerialNetwork__p.join(timeout=5)
        assert not vsn._VirtualSerialNetwork__p.is_alive()

        with pytest.raises(VirtualSerialNetworkError):
            vsn.create(1)
    finally:
        vsn.stop()
        assert vsn._VirtualSerialNetwork__p is None


def test_mid_command_worker_death_raises(logger_fixture):
    """A worker killed mid-command makes the next command raise instead of hanging.

    SIGKILL is sent without joining, so the worker is still alive when the next
    command is issued. start() has already closed the parent's copy of the worker's
    pipe end, so once the worker dies the parent's recv() sees EOF and is converted
    to VirtualSerialNetworkError. If the worker is reaped before the liveness check,
    _ensure_worker_alive raises the same error, so either path passes.
    """
    vsn = VirtualSerialNetwork(virtual_ports_num=2, logger=logger_fixture)
    vsn.start()
    try:
        os.kill(vsn._VirtualSerialNetwork__p.pid, signal.SIGKILL)
        with pytest.raises(VirtualSerialNetworkError):
            vsn.create(1)
    finally:
        vsn.stop()
        assert vsn._VirtualSerialNetwork__p is None


def test_stop_tolerates_dead_worker(logger_fixture):
    """stop() completes without raising and clears the handle for a dead worker.

    This also covers the SIGKILL fallback's observable contract indirectly: the
    worker blocks SIGTERM by design (worker.py pthread_sigmask), so terminate()
    would be a no-op and leak a signal-immune process. The kill()-based fallback is
    not directly unit-tested because the only deterministic way to hang the real
    worker is a blocking openpty_func injection, and a sleep-based test would be
    flaky. stop() on a SIGKILLed worker completing without raising and clearing __p
    is the observable guarantee that matters.
    """
    vsn = VirtualSerialNetwork(virtual_ports_num=2, logger=logger_fixture)
    vsn.start()
    os.kill(vsn._VirtualSerialNetwork__p.pid, signal.SIGKILL)
    vsn._VirtualSerialNetwork__p.join(timeout=5)
    assert not vsn._VirtualSerialNetwork__p.is_alive()

    vsn.stop()
    assert vsn._VirtualSerialNetwork__p is None
