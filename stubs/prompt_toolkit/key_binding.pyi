
from typing import List


class KeyBindingsBase(object):
    pass


class KeyBindings(KeyBindingsBase):
    def __init__(self) -> None: ...


def merge_key_bindings(bindings: List[KeyBindings]) -> KeyBindingsBase: ...
