"""
Synthetic vendor plugin used to exercise the gateway's non-standard path.

This package is a *test fixture*, not production code. It implements a tiny
command-based vendor protocol so the gateway's translator pipeline can be
verified end-to-end without depending on a real vendor package.

Protocol (deliberately shaped like a real ASCII vendor protocol):

    <3-digit dev_id><command><data><checksum>\\r

Commands:
    - ``"R"`` + 2-digit register address -> 4-digit decimal value.

The standard Modbus side maps FC03 (read holding registers) onto ``"R"``.
"""
