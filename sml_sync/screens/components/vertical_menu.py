from collections import namedtuple

from typing import List

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Window, FormattedTextControl

MenuEntry = namedtuple('MenuEntry', ['id_', 'text'])


class VerticalMenu(object):

    def __init__(self, entries: List[MenuEntry]):
        self._current_index = 0
        self._entries = entries
        self._control = FormattedTextControl(
            '', focusable=True, show_cursor=False,
            key_bindings=self._get_key_bindings())
        self._set_control_text()
        self._window = Window(self._control)
        self._menu_change_callbacks = []

    @property
    def current_selection(self):
        return self._entries[self._current_index].id_

    def register_menu_change_callback(self, callback):
        self._menu_change_callbacks.append(callback)

    def _execute_callbacks(self, new_selection):
        for callback in self._menu_change_callbacks:
            callback(new_selection)

    def _select_next(self):
        self._set_selection_index(self._current_index + 1)

    def _select_previous(self):
        self._set_selection_index(self._current_index - 1)

    def _get_key_bindings(self):
        bindings = KeyBindings()

        @bindings.add('up')  # noqa: F811
        def _(event):
            self._select_previous()

        @bindings.add('down')  # noqa: F811
        def _(event):
            self._select_next()

        return bindings

    def _set_selection_index(self, new_index):
        new_index = new_index % len(self._entries)
        if self._current_index != new_index:
            self._current_index = new_index
            self._set_control_text()
            self._execute_callbacks(self.current_selection)

    def _set_control_text(self):
        control_lines = []
        for ientry, entry in enumerate(self._entries):
            style = 'reverse' if ientry == self._current_index else ''
            control_lines.append((style, entry.text + '\n'))
        self._control.text = control_lines

    def __pt_container__(self):
        return self._window
