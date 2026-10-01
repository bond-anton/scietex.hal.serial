"""
Plugin loader for the Modbus gateway.

Resolves plugin references from configuration into concrete classes. Two forms
are supported:

- Built-in framer shortcuts: ``"RTU"`` and ``"ASCII"`` map to the pymodbus
  framer classes. ``"SOCKET"``/``"TLS"`` are rejected (the gateway bus is
  serial). Shortcuts are uppercase, matching `FramerType` member names and the
  existing `ModbusSerialConnectionConfig.framer` convention.
- Dotted-path strings: ``"mypackage.MyFramer"`` is imported and returned.

The loader performs no instantiation beyond framers (which need a decoder);
callers construct the resolved classes as needed.

Functions:
    - load_class: Import a class from a dotted-path string.
    - resolve_framer: Resolve a framer reference to a `FramerBase` subclass.
    - resolve_decoder: Resolve a decoder reference to a `DecodePDU` subclass.
    - resolve_pdu: Resolve a PDU reference to a `ModbusPDU` subclass.
    - resolve_translator: Resolve a translator reference to a `GatewayTranslator`
      subclass.
    - build_framer: Instantiate a framer with a decoder.
"""

import importlib
from typing import TYPE_CHECKING, Any, TypeVar

from pymodbus import FramerType
from pymodbus.framer import FRAMER_NAME_TO_CLASS, FramerBase
from pymodbus.pdu import DecodePDU, ModbusPDU

from .exceptions import GatewayConfigError

if TYPE_CHECKING:
    pass

# Built-in framer shortcuts. "SOCKET"/"TLS" are excluded: the gateway bus is
# serial, so only RTU and ASCII are meaningful. Uppercase matches FramerType
# member names and ModbusSerialConnectionConfig.framer.
_BUILTIN_FRAMERS: dict[str, FramerType] = {
    "RTU": FramerType.RTU,
    "ASCII": FramerType.ASCII,
}

_T = TypeVar("_T")


def load_class(dotted_path: str) -> type:
    """
    Import and return a class from a dotted-path string.

    Args:
        dotted_path (str): Fully qualified class path, e.g. ``"mypackage.MyClass"``.

    Returns:
        type: The resolved class object.

    Raises:
        GatewayConfigError: If the path is malformed, the module cannot be
            imported, or the attribute is missing.
    """
    module_path, _, class_name = dotted_path.rpartition(".")
    if not module_path or not class_name:
        raise GatewayConfigError(
            f"Invalid dotted path: {dotted_path!r} (expected 'module.ClassName')"
        )
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise GatewayConfigError(f"Cannot import module {module_path!r}: {exc}") from exc
    try:
        return getattr(module, class_name)
    except AttributeError as exc:
        raise GatewayConfigError(f"Module {module_path!r} has no attribute {class_name!r}") from exc


def _resolve_subclass(
    reference: str,
    base: type[_T],
    kind: str,
    builtins: dict[str, Any] | None = None,
) -> type[_T]:
    """
    Resolve a reference to a subclass of `base`.

    Args:
        reference (str): Built-in shortcut or dotted path.
        base (type[_T]): Required base class.
        kind (str): Human-readable kind for error messages (e.g. "framer").
        builtins (dict[str, Any] | None): Optional shortcut-to-class mapping.

    Returns:
        type[_T]: The resolved subclass.

    Raises:
        GatewayConfigError: If the reference is unknown or not a subclass of `base`.
    """
    if builtins is not None and reference in builtins:
        resolved = builtins[reference]
    else:
        resolved = load_class(reference)
    if not isinstance(resolved, type) or not issubclass(resolved, base):
        raise GatewayConfigError(
            f"Resolved {kind} {reference!r} is not a subclass of {base.__name__}"
        )
    return resolved


def resolve_framer(reference: str) -> type[FramerBase]:
    """
    Resolve a framer reference to a `FramerBase` subclass.

    Args:
        reference (str): ``"RTU"``, ``"ASCII"``, or a dotted path.

    Returns:
        type[FramerBase]: The resolved framer class.

    Raises:
        GatewayConfigError: If the reference is unknown or not a framer.
    """
    builtins = {
        name: FRAMER_NAME_TO_CLASS[framer_type] for name, framer_type in _BUILTIN_FRAMERS.items()
    }
    return _resolve_subclass(reference, FramerBase, "framer", builtins)


def resolve_decoder(reference: str) -> type[DecodePDU]:
    """
    Resolve a decoder reference to a `DecodePDU` subclass.

    Args:
        reference (str): Dotted path to a decoder class.

    Returns:
        type[DecodePDU]: The resolved decoder class.

    Raises:
        GatewayConfigError: If the reference is unknown or not a decoder.
    """
    return _resolve_subclass(reference, DecodePDU, "decoder")


def resolve_pdu(reference: str) -> type[ModbusPDU]:
    """
    Resolve a PDU reference to a `ModbusPDU` subclass.

    Args:
        reference (str): Dotted path to a PDU class.

    Returns:
        type[ModbusPDU]: The resolved PDU class.

    Raises:
        GatewayConfigError: If the reference is unknown or not a PDU.
    """
    return _resolve_subclass(reference, ModbusPDU, "pdu")


def resolve_translator(reference: str) -> type[Any]:
    """
    Resolve a translator reference to a `GatewayTranslator` subclass.

    The `GatewayTranslator` protocol is imported lazily to avoid a circular
    import between the loader and the translator module.

    Args:
        reference (str): Dotted path to a translator class.

    Returns:
        type[Any]: The resolved translator class.

    Raises:
        GatewayConfigError: If the reference is unknown or not a translator.
    """
    from .translator import GatewayTranslator

    return _resolve_subclass(reference, GatewayTranslator, "translator")


def build_framer(framer_cls: type[FramerBase], decoder: DecodePDU) -> FramerBase:
    """
    Instantiate a framer with a decoder.

    Args:
        framer_cls (type[FramerBase]): The framer class to instantiate.
        decoder (DecodePDU): The decoder the framer uses to interpret PDUs.

    Returns:
        FramerBase: A framer instance.
    """
    return framer_cls(decoder)
