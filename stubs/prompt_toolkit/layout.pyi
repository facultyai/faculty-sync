
from typing import Optional, Any, List, Iterable, Union, Tuple

from .key_binding import KeyBindings
from .buffer import Buffer


class UIControl(object):

    def reset(self) -> None: ...


class FormattedTextControl(UIControl):

    text: Union[str, List[Tuple[str, str]]]

    def __init__(
            self,
            text: Union[str, List[Tuple[str, str]]],
            focusable: bool = False,
            show_cursor: bool = False,
            key_bindings: Optional[KeyBindings] = None) -> None: ...


class BufferControl(UIControl):

    def __init__(
            self,
            buffer: Optional[Buffer] = None
    ) -> None: ...


class Margin(object):
    pass


class ScrollbarMargin(Margin):

    def __init__(self, display_arrows: int = 2) -> None: ...


class Container(object):

    def reset(self) -> None: ...

    def preferred_width(self, max_available_width: int) -> int: ...

    def preferred_height(
            self,
            width: int,
            max_available_height: int
    ) -> int: ...


class Window(Container):

    def __init__(
            self,
            content: Optional[UIControl] = None,
            width: Optional[int] = None,
            height: Optional[int] = None,
            left_margins: Optional[Iterable[Margin]] = None,
            right_margins: Optional[Iterable[Margin]] = None
    ) -> None: ...


class HSplit(Container):

    def __init__(
            self,
            children: List[Any],
            width: Optional[int] = None,
            height: Optional[int] = None
    ) -> None: ...


class VSplit(Container):

    def __init__(
            self,
            children: List[Any],
            width: Optional[int] = None,
            height: Optional[int] = None
    ) -> None: ...


class Float(object):

    def __init__(
            self,
            content: Optional[Container]
    ) -> None: ...


class FloatContainer(Container):

    def __init__(
            self,
            content: Container,
            floats: Iterable[Float]
    ) -> None: ...


def to_container(container: Any) -> Container: ...


class Layout(object):

    def __init__(
            self,
            container: Container
    ) -> None: ...
