# Virtual Serial Network

The `virtual` module creates PTY-backed serial ports so you can exercise the
client, server, and gateway without any hardware. It is Linux/macOS only.

## A virtual pair

A `VirtualSerialPair` gives you two connected ports — write to one, read from
the other:

```python
from scietex.hal.serial import VirtualSerialPair

if __name__ == "__main__":
    vsp = VirtualSerialPair()
    vsp.start()
    print(vsp.serial_ports)

    vsp.stop()
```

## A virtual network

`VirtualSerialNetwork` connects multiple virtual ports, and can bridge to
external physical ports:

```python
from scietex.hal.serial import SerialConnectionConfig, VirtualSerialNetwork

if __name__ == "__main__":
    vsn1 = VirtualSerialNetwork(virtual_ports_num=3)
    vsn1.start()
    print(f"VSN 1 ports: {vsn1.serial_ports}")

    vsn2 = VirtualSerialNetwork(virtual_ports_num=2)
    vsn2.start()

    vsn2.add([SerialConnectionConfig(vsn1.serial_ports[0])])

    vsn1.create(2)
    print(f"VSN 1 ports: {vsn1.serial_ports}")
    print(f"VSN 2 ports: {vsn2.serial_ports}")

    vsn1.stop()
    vsn2.stop()
```

## How it works

The port-forwarding loop runs in a separate `multiprocessing` process, driven
over a `Pipe`. The parent sends `create`/`add`/`remove`/`stop` commands; the
worker blocks `SIGINT`/`SIGTERM` so the parent controls shutdown. If the worker
dies unexpectedly, the parent raises `VirtualSerialNetworkError` rather than
hanging.

See the [Virtual API reference](../api/virtual.md) for details.
