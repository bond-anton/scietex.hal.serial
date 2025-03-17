"""Example of VirtualSerialNetwork class usage."""

from scietex.hal.serial import VirtualSerialNetwork, SerialConnectionConfig

if __name__ == "__main__":
    vsn1 = VirtualSerialNetwork(virtual_ports_num=3)
    vsn1.start()
    print(f"VSN 1 ports: {vsn1.serial_ports}")

    vsn2 = VirtualSerialNetwork(virtual_ports_num=2)
    vsn2.start()

    vsn2.add([SerialConnectionConfig(vsn1.serial_ports[0])])

    # Create two more virtual ports
    vsn1.create(2)

    print(f"VSN 1 ports: {vsn1.serial_ports}")
    print(f"VSN 2 ports: {vsn2.serial_ports}")

    vsn1.stop()
    vsn2.stop()
