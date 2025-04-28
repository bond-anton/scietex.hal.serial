"""Find serial ports by VID/PID."""

import serial.tools.list_ports


# STM32 constants.
STM_VID = 0x0483  # STMicroelectronics
STM_PID = 0x5740  # CDC Virtual COM Port

STM_CDC_DEVICES = {STM_VID: [STM_PID]}

# RS485 usb converter constants.
RS485_DEVICES = {0x1A86: [0x7523]}  # Sunplus Technology Inc.


def find_serial_ports(vid_pid_mapping: dict[int, list[int]]) -> list[str]:
    """Find serial ports by VID/PID."""
    ports = serial.tools.list_ports.comports()
    selected_ports = []
    for port in ports:
        if port.vid in vid_pid_mapping:
            if port.pid in vid_pid_mapping[port.vid]:
                selected_ports.append(port.device)
    return selected_ports


def find_stm32_cdc() -> list[str]:
    """Find STM32 CDC devices."""
    return find_serial_ports(STM_CDC_DEVICES)


def find_rs485() -> list[str]:
    """Find RS485 USB converters."""
    return find_serial_ports(RS485_DEVICES)
