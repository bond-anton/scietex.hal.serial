"""Example of VirtualSerialPair class usage."""

from scietex.hal.serial import VirtualSerialPair

if __name__ == "__main__":
    vsp = VirtualSerialPair()
    vsp.start()
    # Now your virtual serial pair is ready
    print(vsp.serial_ports)

    vsp.stop()
