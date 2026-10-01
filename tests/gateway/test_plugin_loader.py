"""Test the gateway plugin loader."""

import pytest
from pymodbus.framer import FramerAscii, FramerRTU
from pymodbus.pdu import DecodePDU

try:
    from src.scietex.hal.serial.gateway.exceptions import GatewayConfigError
    from src.scietex.hal.serial.gateway.plugin_loader import (
        build_framer,
        load_class,
        resolve_decoder,
        resolve_framer,
        resolve_pdu,
        resolve_translator,
    )
    from src.scietex.hal.serial.gateway.translator import GatewayTranslator
except ModuleNotFoundError:
    from scietex.hal.serial.gateway.exceptions import GatewayConfigError
    from scietex.hal.serial.gateway.plugin_loader import (
        build_framer,
        load_class,
        resolve_decoder,
        resolve_framer,
        resolve_pdu,
        resolve_translator,
    )
    from scietex.hal.serial.gateway.translator import GatewayTranslator


def test_resolve_builtin_framers():
    """Built-in shortcuts map to the pymodbus framer classes."""
    assert resolve_framer("RTU") is FramerRTU
    assert resolve_framer("ASCII") is FramerAscii


def test_resolve_framer_dotted_path():
    """A dotted path resolves to the same class as the shortcut."""
    assert resolve_framer("pymodbus.framer.FramerRTU") is FramerRTU


@pytest.mark.parametrize("reference", ["SOCKET", "TLS"])
def test_resolve_framer_rejects_non_serial(reference):
    """Socket/TLS framers are not valid on a serial bus."""
    with pytest.raises(GatewayConfigError):
        resolve_framer(reference)


def test_resolve_decoder():
    """A dotted path resolves to a DecodePDU subclass."""
    assert resolve_decoder("pymodbus.pdu.DecodePDU") is DecodePDU


def test_resolve_pdu_rejects_non_pdu():
    """A class that is not a ModbusPDU subclass is rejected."""
    with pytest.raises(GatewayConfigError):
        resolve_pdu("pymodbus.framer.FramerRTU")


class _Translator:
    """Minimal translator implementation for loader tests."""

    def to_vendor(self, request):
        return request

    def to_standard(self, response):
        return response


def test_resolve_translator_accepts_protocol_impl():
    """A class implementing the translator protocol resolves."""
    assert resolve_translator(f"{_Translator.__module__}._Translator") is _Translator


def test_resolve_translator_rejects_non_translator():
    """A class not implementing the protocol is rejected."""
    with pytest.raises(GatewayConfigError):
        resolve_translator("pymodbus.framer.FramerRTU")


def test_load_class_invalid_path():
    """A path without a module separator is rejected."""
    with pytest.raises(GatewayConfigError):
        load_class("notadottedpath")


def test_load_class_missing_module():
    """A missing module is reported as a config error."""
    with pytest.raises(GatewayConfigError):
        load_class("no_such_module_xyz.Thing")


def test_load_class_missing_attribute():
    """A missing attribute is reported as a config error."""
    with pytest.raises(GatewayConfigError):
        load_class("pymodbus.framer.NoSuchFramer")


def test_build_framer():
    """build_framer instantiates the framer with the given decoder."""
    framer = build_framer(FramerRTU, DecodePDU(False))
    assert isinstance(framer, FramerRTU)


def test_translator_protocol_is_runtime_checkable():
    """The protocol supports isinstance checks."""
    assert isinstance(_Translator(), GatewayTranslator)
