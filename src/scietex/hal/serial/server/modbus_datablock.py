"""
Custom reactive DataBlock for Modbus server.

This module defines a custom reactive sequential data block for use in a Modbus server. The primary
goal is to provide enhanced functionality, such as triggering callbacks whenever register values
are changed. This allows for better monitoring and reaction to changes in the server’s state.

Dependencies:
    - pymodbus: Provides base classes and utilities for building Modbus servers and clients.

Classes:
    - ReactiveSequentialDataBlock: Extends the `ModbusSequentialDataBlock` class to implement
      custom behavior upon value changes, such as logging or triggering actions.

Methods:
    - setValues(self, address, values): Overrides the parent class' method to additionally invoke a
      custom callback (`on_change`) when register values are modified.
    - on_change(self, address, values): Callback invoked when register values are changed. Can be
      overridden to perform custom actions, such as logging or event triggering.

This custom data block enhances the capabilities of the Modbus server by providing flexibility
to react to changes in register values dynamically.
"""

from logging import Logger, getLogger
from pymodbus.datastore import ModbusSequentialDataBlock


class ReactiveSequentialDataBlock(ModbusSequentialDataBlock):
    """
    DataBlock with custom action on value change.

    This class extends the `ModbusSequentialDataBlock` to provide customizable behavior when
    register values are modified. It triggers a callback (`on_change`) whenever values are set,
    allowing for dynamic reactions, such as logging or event triggering.

    Attributes:
        logger (Logger): A logging handler for recording debug, info, warning, and error messages.

    Methods:
        - setValues(self, address, values): Overrides the parent class' method to additionally
          invoke a custom callback (`on_change`) when register values are modified.
        - on_change(self, address, values): Callback invoked when register values are changed.
          Can be overridden to perform custom actions, such as logging or event triggering.
    """

    def __init__(self, *args, logger=None, **kwargs):
        """
        Initialize the ReactiveSequentialDataBlock instance.

        Args:
            *args: Positional arguments passed to the parent constructor.
            logger (Optional[Logger], optional): A logging handler for recording operational
                information. Defaults to a basic logger if none is provided.
            **kwargs: Keyword arguments passed to the parent constructor.
        """
        super().__init__(*args, **kwargs)
        self.logger = logger if isinstance(logger, Logger) else getLogger()

    def setValues(self, address, values):
        """
        Set register values with custom callback.

        This method overrides the parent class’ `setValues` method to additionally invoke a custom
        callback (`on_change`) when register values are modified.

        Args:
            address (int): Starting address of the register(s) to modify.
            values (list[int]): New values to assign to the registers.

        Notes:
            - Invokes the `on_change` callback after modifying the register values.
        """
        super().setValues(address, values)
        self.on_change(address, values)

    def on_change(self, address, values):
        """
        Register value change callback.

        This method is called automatically whenever register values are modified through
        `setValues`. By default, it logs the change, but it can be overridden to perform custom
        actions.

        Args:
            address (int): Starting address of the modified register(s).
            values (list[int]): New values assigned to the registers.

        Notes:
            - This method can be extended or replaced entirely to implement custom behavior.
        """
        self.logger.debug("Register %s changed value to %s", address, values)
