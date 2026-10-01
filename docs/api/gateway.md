# Gateway

A serial↔TCP Modbus gateway. It owns one serial port, accepts standard
Modbus/TCP clients, and routes requests to the bus by device id. Non-Modbus
vendor devices are supported through a `GatewayTranslator` plugin.

See the [Modbus Gateway user guide](../guide/gateway.md) for a worked example,
and the [design document](../design/modbus-gateway.md) for the rationale.

## Core

::: scietex.hal.serial.gateway.gateway
    options:
      members:
        - ModbusGateway

::: scietex.hal.serial.gateway.tcp_server
    options:
      members:
        - GatewayTcpServer

## Configuration

::: scietex.hal.serial.gateway.config
    options:
      members:
        - GatewayConfig
        - GatewayDeviceConfig

## Translator protocol

::: scietex.hal.serial.gateway.translator
    options:
      members:
        - GatewayTranslator

## Plugin loader

::: scietex.hal.serial.gateway.plugin_loader
    options:
      members:
        - load_class
        - resolve_framer
        - resolve_decoder
        - resolve_pdu
        - resolve_translator
        - build_framer

## Exceptions

::: scietex.hal.serial.gateway.exceptions
    options:
      members:
        - GatewayError
        - GatewayConfigError
