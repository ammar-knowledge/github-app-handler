"""Module to create a spy"""

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch


@contextmanager
def spy(clazz: type) -> patch:
    """
    Spy Method

    :param clazz: The class to be spied on.
    :return: spied class

    This method spies on a given class by replacing the `__init__` method of the class with a spy implementation.
    This allows us to intercept and mock method calls made on the class instance.

    The spy implementation (`spy_init`) is defined within the `spy` method.
    It wraps around the original `__init__` method of the class and replaces all the callable attributes of the
    class instance with a `MagicMock` object that mimics the original method's behavior.
     This enables us to track and validate method calls.

    Note that built-in methods (those starting and ending with double underscores) are
    skipped and not replaced with a spy.

    Example usage:

    ```python
    class MyClass:
        def __init__(self, value):
            self.value = value

        def perform_action(self):
            print("Performing action")

    # Spying on the MyClass
    spy(MyClass)

    # Creating an instance of MyClass
    obj = MyClass(10)

    # Now the method calls on obj will be tracked and mocked
    obj.perform_action()  # This will be intercepted and tracked, but not executed
    ```
    """
    original_init = clazz.__init__

    def spy_init(self: Any, *args, **kwargs) -> None:
        """Replaces the original `__init__` to replaces all the callable attributes with a MagicMock"""
        original_init(self, *args, **kwargs)
        for name in dir(self):
            # skipping builtin methods
            if name.startswith("__") and name.endswith("__"):
                continue
            if callable(method := getattr(self, name)):
                setattr(self, name, MagicMock(side_effect=method))

    with patch.object(clazz, "__init__", spy_init):
        yield
