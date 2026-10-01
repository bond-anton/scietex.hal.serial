"""Example of find_serial_ports utility usage."""

from scietex.hal.serial.utilities.serial_port_finder import (
    STM_CDC_DEVICES,
    find_rs485,
    find_serial_ports,
    find_stm32_cdc,
)


def main() -> None:
    """Search for STM32 CDC and RS485 USB devices by VID/PID."""
    print("STM32 CDC devices mapping:", STM_CDC_DEVICES)
    stm32_cdc_devices = find_serial_ports(STM_CDC_DEVICES)
    print("STM32 CDC devices:", stm32_cdc_devices)

    stm32_cdc_devices = find_stm32_cdc()
    print("STM32 CDC devices:", stm32_cdc_devices)

    rs485_ports = find_rs485()
    print("RS485 ports:", rs485_ports)


if __name__ == "__main__":
    main()
