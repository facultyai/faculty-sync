
from typing import List, Callable, Any


class KeyBindingsBase(object):
    pass


class KeyBindings(KeyBindingsBase):
    def __init__(self) -> None: ...

    def add(self, key: str) -> Callable[..., Any]: ...


def merge_key_bindings(bindings: List[KeyBindings]) -> KeyBindingsBase: ...
