"""Find serial ports by VID/PID.

Overridable hardware profiles live in :data:`DEVICE_PROFILES`, a registry
mapping profile names to VID/PID maps. Pass a custom mapping to the
convenience helpers to override the built-in profiles.
"""

import serial.tools.list_ports

#: Registry of hardware profiles mapping profile names to VID/PID maps.
DEVICE_PROFILES: dict[str, dict[int, list[int]]] = {
    "stm32_cdc": {0x0483: [0x5740]},  # STMicroelectronics CDC Virtual COM Port
    "rs485": {0x1A86: [0x7523]},  # Sunplus Technology Inc.
}

#: USB vendor ID for STMicroelectronics.
STM_VID = 0x0483
#: USB product ID for the STM32 CDC Virtual COM Port.
STM_PID = 0x5740

#: VID/PID mapping for STM32 CDC virtual COM ports.
STM_CDC_DEVICES = DEVICE_PROFILES["stm32_cdc"]

#: VID/PID mapping for RS485 USB converters.
RS485_DEVICES = DEVICE_PROFILES["rs485"]


def find_serial_ports(vid_pid_mapping: dict[int, list[int]]) -> list[str]:
    """Find serial ports matching a VID/PID mapping.

    Scans all system serial ports and returns the device paths of ports whose
    VID/PID pair is present in ``vid_pid_mapping``.

    Args:
        vid_pid_mapping (dict[int, list[int]]): Mapping of USB vendor IDs to
            lists of product IDs.

    Returns:
        list[str]: Device paths of the matching serial ports.
    """
    ports = serial.tools.list_ports.comports()
    selected_ports = []
    for port in ports:
        if port.vid in vid_pid_mapping:
            if port.pid in vid_pid_mapping[port.vid]:
                selected_ports.append(port.device)
    return selected_ports


def find_stm32_cdc(mapping: dict[int, list[int]] | None = None) -> list[str]:
    """Find STM32 CDC virtual COM ports.

    Convenience wrapper over :func:`find_serial_ports` using the built-in
    ``stm32_cdc`` profile unless a custom mapping is supplied.

    Args:
        mapping (dict[int, list[int]] | None, optional): Custom VID/PID mapping.
            Defaults to the built-in ``stm32_cdc`` profile.

    Returns:
        list[str]: Device paths of the matching STM32 CDC ports.
    """
    return find_serial_ports(mapping if mapping is not None else DEVICE_PROFILES["stm32_cdc"])


def find_rs485(mapping: dict[int, list[int]] | None = None) -> list[str]:
    """Find RS485 USB converter ports.

    Convenience wrapper over :func:`find_serial_ports` using the built-in
    ``rs485`` profile unless a custom mapping is supplied.

    Args:
        mapping (dict[int, list[int]] | None, optional): Custom VID/PID mapping.
            Defaults to the built-in ``rs485`` profile.

    Returns:
        list[str]: Device paths of the matching RS485 converter ports.
    """
    return find_serial_ports(mapping if mapping is not None else DEVICE_PROFILES["rs485"])
