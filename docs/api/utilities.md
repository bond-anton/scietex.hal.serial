# Utilities

Checksums, numeric helpers, Modbus helpers, and serial-port discovery.

## Checksums

::: scietex.hal.serial.utilities.checksum
    options:
      members:
        - check_sum
        - lrc
        - check_lrc

## Numeric helpers

::: scietex.hal.serial.utilities.numeric
    options:
      members:
        - ByteOrder
        - to_signed16
        - from_signed16
        - to_signed32
        - from_signed32
        - combine_32bit
        - split_32bit
        - float_from_int
        - float_to_unsigned16
        - float_from_unsigned16
        - float_from_unsigned32

## Modbus helpers

::: scietex.hal.serial.utilities.modbus
    options:
      members:
        - ModbusOperationError
        - modbus_connection_config
        - modbus_get_client
        - modbus_connection
        - modbus_execute
        - modbus_read_registers
        - modbus_read_input_registers
        - modbus_read_holding_registers
        - modbus_write_registers
        - modbus_write_register

## Serial port discovery

::: scietex.hal.serial.utilities.serial_port_finder
    options:
      members:
        - DEVICE_PROFILES
        - find_serial_ports
        - find_stm32_cdc
        - find_rs485
