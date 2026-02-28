"""Example of VirtualSerialNetwork class usage."""

import logging
import time

from scietex.hal.serial import VirtualSerialNetwork, SerialConnectionConfig


def get_colored_logger(name, level=logging.DEBUG):
    """Creates a logger with colored output based on the log level."""
    data_logger = logging.getLogger(name)
    data_logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)8s %(name)s → %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)

    class ColorFormatter(logging.Formatter):
        """Custom formatter to add colors to log messages based on their level."""

        LEVEL_COLORS = {
            logging.DEBUG: "\x1b[36m",  # cyan
            logging.INFO: "\x1b[32m",  # green
            logging.WARNING: "\x1b[33m",  # yellow
            logging.ERROR: "\x1b[31m",  # red
            logging.CRITICAL: "\x1b[35m",  # magenta
        }

        def format(self, record):
            color = self.LEVEL_COLORS.get(record.levelno, "")
            msg = super().format(record)
            return f"{color}{msg}\x1b[0m"

    handler.setFormatter(
        ColorFormatter(
            "%(asctime)s %(levelname)8s %(name)s → %(message)s", datefmt="%H:%M:%S"
        )
    )

    data_logger.addHandler(handler)
    return data_logger


if __name__ == "__main__":
    logger = get_colored_logger("VSN Example", level=logging.DEBUG)
    vsn1 = VirtualSerialNetwork(
        virtual_ports_num=4,
        logger=logger,
        data_log_dir="data_logs/vsn1",
        data_logging_splitter=b"\n",
    )
    vsn1.start()
    print(f"VSN 1 ports: {vsn1.serial_ports}")

    shared_port = vsn1.serial_ports[0]
    print(f"Shared port: {shared_port}")

    vsn2 = VirtualSerialNetwork(
        virtual_ports_num=0,
        external_ports=[SerialConnectionConfig(port=shared_port)],
        logger=logger,
        data_log_dir="data_logs/vsn2",
        data_logging_splitter=b"\n",
    )
    vsn2.start()
    print(f"VSN 2 ports: {vsn2.serial_ports}")

    # Create two more virtual ports
    vsn2.create(2)

    print(f"VSN 2 ports: {vsn2.serial_ports}")

    vsn1_talk_port = vsn1.serial_ports[1]
    vsn1_read_port = vsn1.serial_ports[2]
    i = 0
    vsn2_talk_port = vsn2.serial_ports[i]
    while vsn2_talk_port == shared_port:
        i += 1
        vsn2_talk_port = vsn2.serial_ports[i]
    i = 0
    vsn2_read_port = vsn2.serial_ports[i]
    while vsn2_read_port in [shared_port, vsn2_talk_port]:
        i += 1
        vsn2_read_port = vsn2.serial_ports[i]

    print(f"VSN 1 talk port: {vsn1_talk_port}")
    print(f"VSN 1 read port: {vsn1_read_port}")
    print(f"VSN 2 talk port: {vsn2_talk_port}")
    print(f"VSN 2 read port: {vsn2_read_port}")

    # pylint: disable=consider-using-with
    vsn1_w_port = open(vsn1_talk_port, "wb", buffering=0)
    vsn1_r_port = open(vsn1_read_port, "rb", buffering=0)

    vsn2_w_port = open(vsn2_talk_port, "wb", buffering=0)
    vsn2_r_port = open(vsn2_read_port, "rb", buffering=0)

    # Send payload from VSN1
    test_data = b"Hello, World!\n"
    print(f"Sending data from VSN 1: {test_data}")
    vsn1_w_port.write(test_data)
    time.sleep(0.5)  # Wait for data to be forwarded
    # Read payload from VSN1
    received_data = vsn1_r_port.read(len(test_data))
    print(f"Received data on VSN 1: {received_data}")
    # Read payload from VSN2
    received_data = vsn2_r_port.read(len(test_data))
    print(f"Received data on VSN 2: {received_data}")

    # Send payload from VSN2
    test_data = b"Hello, World again!\n"
    print(f"Sending data from VSN 2: {test_data}")
    vsn2_w_port.write(test_data)
    time.sleep(0.5)  # Wait for data to be forwarded
    # Read payload from VSN1
    received_data = vsn1_r_port.read(len(test_data))
    print(f"Received data on VSN 1: {received_data}")
    # Read payload from VSN2
    received_data = vsn2_r_port.read(len(test_data))
    print(f"Received data on VSN 2: {received_data}")

    vsn1_w_port.close()
    vsn1_r_port.close()
    vsn2_w_port.close()
    vsn2_r_port.close()

    vsn1.stop()
    vsn2.stop()
