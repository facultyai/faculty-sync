from collections import namedtuple

from typing import List, Optional, Any, Callable

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Window, FormattedTextControl, Container

MenuEntry = namedtuple('MenuEntry', ['id_', 'text'])


class VerticalMenu(object):

    def __init__(
            self,
            entries: List[MenuEntry],
            width: Optional[int] = None
    ) -> None:
        self._current_index = 0
        self._entries = entries
        if width is None:
            self._formatted_entries = [entry.text for entry in self._entries]
        else:
            self._formatted_entries = [
                _ensure_width(entry.text, width) for entry in self._entries
            ]
        self._control = FormattedTextControl(
            '', focusable=True, show_cursor=False,
            key_bindings=self._get_key_bindings())
        self._set_control_text()
        self._window = Window(self._control, width=width)
        self._menu_change_callbacks: List[Callable[[Any], None]] = []

    @property
    def current_selection(self) -> Any:
        if self._entries:
            return self._entries[self._current_index].id_
        else:
            # No items in the menu
            return None

    def register_menu_change_callback(
            self,
            callback: Callable[[Any], None]
    ) -> None:
        self._menu_change_callbacks.append(callback)

    def _execute_callbacks(self, new_selection: Any) -> None:
        for callback in self._menu_change_callbacks:
            callback(new_selection)

    def _select_next(self) -> None:
        self._set_selection_index(self._current_index + 1)

    def _select_previous(self) -> None:
        self._set_selection_index(self._current_index - 1)

    def _get_key_bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        @bindings.add('up')
        def up_key(event: Any) -> None:
            self._select_previous()

        @bindings.add('down')
        def down_key(event: Any) -> None:
            self._select_next()

        return bindings

    def _set_selection_index(self, new_index: int) -> None:
        if self._entries:
            new_index = new_index % len(self._entries)
            if self._current_index != new_index:
                self._current_index = new_index
                self._set_control_text()
                self._execute_callbacks(self.current_selection)

    def _set_control_text(self) -> None:
        control_lines = []
        for ientry, entry in enumerate(self._formatted_entries):
            style = 'reverse' if ientry == self._current_index else ''
            control_lines.append((style, entry + '\n'))
        self._control.text = control_lines

    def __pt_container__(self) -> Container:
        return self._window


def _ensure_width(inp: str, width: int) -> str:
    """
    Ensure that string `inp` is exactly `width` characters long.
    """
    return inp[:width].ljust(width)
