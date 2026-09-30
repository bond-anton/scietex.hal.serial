"""Find serial ports by VID/PID.

Overridable hardware profiles live in :data:`DEVICE_PROFILES`, a registry
mapping profile names to VID/PID maps. Pass a custom mapping to the
convenience helpers to override the built-in profiles.
"""

import serial.tools.list_ports

DEVICE_PROFILES: dict[str, dict[int, list[int]]] = {
    "stm32_cdc": {0x0483: [0x5740]},  # STMicroelectronics CDC Virtual COM Port
    "rs485": {0x1A86: [0x7523]},  # Sunplus Technology Inc.
}

# STM32 constants.
STM_VID = 0x0483  # STMicroelectronics
STM_PID = 0x5740  # CDC Virtual COM Port

STM_CDC_DEVICES = DEVICE_PROFILES["stm32_cdc"]

# RS485 usb converter constants.
RS485_DEVICES = DEVICE_PROFILES["rs485"]


def find_serial_ports(vid_pid_mapping: dict[int, list[int]]) -> list[str]:
    """Find serial ports by VID/PID."""
    ports = serial.tools.list_ports.comports()
    selected_ports = []
    for port in ports:
        if port.vid in vid_pid_mapping:
            if port.pid in vid_pid_mapping[port.vid]:
                selected_ports.append(port.device)
    return selected_ports


def find_stm32_cdc(mapping: dict[int, list[int]] | None = None) -> list[str]:
    """Find STM32 CDC devices, optionally using a custom VID/PID mapping."""
    return find_serial_ports(mapping if mapping is not None else DEVICE_PROFILES["stm32_cdc"])


def find_rs485(mapping: dict[int, list[int]] | None = None) -> list[str]:
    """Find RS485 USB converters, optionally using a custom VID/PID mapping."""
    return find_serial_ports(mapping if mapping is not None else DEVICE_PROFILES["rs485"])
