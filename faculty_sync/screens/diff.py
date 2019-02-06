import logging
from enum import Enum

from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, VSplit, to_container
from prompt_toolkit.layout.containers import FloatContainer, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea, VerticalLine

from ..pubsub import Messages
from ..models import DifferenceType
from .base import BaseScreen
from .help import help_modal
from .components import (
    Table,
    TableColumn,
    VerticalMenu,
    MenuEntry,
    ColumnSettings,
    Alignment,
)
from .humanize import naturaltime, naturalsize

HELP_TITLE = "Differences between local directory and Faculty Platform"

HELP_TEXT = """\
Synchronize your local filesystem and the Faculty Platform filesystem.

Three synchronization modes are supported:

'Up' will push all local changes to Faculty Platform. This will
erase any file that is on Faculty Platform, but not available locally.

'Down' will bring all the changes down from Faculty Platform. This
will erase any file that is present locally but not on Faculty Platform.

'Watch' enters `watch` mode. Any time you save, move or delete
a file or a directory, the change is automatically replicated
on Faculty Platform.

Keys:

    [left/right] Switch focus between the left-hand menu and
                 the action lists.
    [up/down] Navigate the left-hand menu or the table of
              files, depending on which one is focussed.
    [r] Refresh differences between the local file system
        and Faculty Platform.
    [q] Quit the application.
    [?] Toggle this message.
"""


UP_SYNC_HELP_TEXT = """\
Press [u] to modify the Faculty Platform workspace so that it mirrors your local disk.

This will make the following changes to your Faculty Platform workspace:
"""

DOWN_SYNC_HELP_TEXT = """\
Press [d] to modify your local filesystem so that it mirrors the Faculty Platform workspace.

This will make the following changes to your local disk:
"""

WATCH_HELP_TEXT = """\
Press [w] to enter `watch` mode. Any time you save, move or delete a file, the change is automatically replicated on Faculty Platform.
"""

FULLY_SYNCHRONIZED_HELP_TEXT = """\
Your local disk and the Faculty Platform workspace are fully synchronized.
"""


class SelectionName(Enum):
    UP = "UP"
    DOWN = "DOWN"
    WATCH = "WATCH"


class DiffScreenMessages(Enum):
    """
    Messages used internally in the differences screen
    """

    SELECTION_UPDATED = "SELECTION_UPDATED"


ACTION_TEXT = {
    (DifferenceType.LEFT_ONLY, SelectionName.UP): "create remote",
    (DifferenceType.RIGHT_ONLY, SelectionName.DOWN): "create local",
    (DifferenceType.LEFT_ONLY, SelectionName.DOWN): "delete local",
    (DifferenceType.RIGHT_ONLY, SelectionName.UP): "delete remote",
    (DifferenceType.TYPE_DIFFERENT, SelectionName.UP): "replace remote",
    (DifferenceType.TYPE_DIFFERENT, SelectionName.DOWN): "replace local",
    (DifferenceType.ATTRS_DIFFERENT, SelectionName.UP): "replace remote",
    (DifferenceType.ATTRS_DIFFERENT, SelectionName.DOWN): "replace local",
}


class Summary(object):
    def __init__(self, exchange):
        self._exchange = exchange
        self._current_index = 0
        self._menu_container = VerticalMenu(
            [
                MenuEntry(SelectionName.UP, "Up"),
                MenuEntry(SelectionName.DOWN, "Down"),
                MenuEntry(SelectionName.WATCH, "Watch"),
            ],
            width=10,
        )
        self._menu_container.register_menu_change_callback(
            lambda new_selection: self._on_new_selection(new_selection)
        )
        self.container = VSplit(
            [
                Window(width=1),
                HSplit([Window(height=1), self._menu_container, Window()]),
            ]
        )

    @property
    def current_selection(self):
        return self._menu_container.current_selection

    @current_selection.setter
    def current_selection(self, new_selection):
        self._menu_container.current_selection = new_selection

    def gain_focus(self, app):
        app.layout.focus(self._menu_container)

    def _on_new_selection(self, new_selection):
        self._exchange.publish(
            DiffScreenMessages.SELECTION_UPDATED, new_selection
        )


class Details(object):
    def __init__(self, exchange, differences, initial_selection):
        self._selection = initial_selection
        self._differences = differences
        self._exchange = exchange
        self._table = None
        self.container = HSplit([])

        self._render()

        self._subscription_id = self._exchange.subscribe(
            DiffScreenMessages.SELECTION_UPDATED, self._set_selection
        )

    def gain_focus_if_possible(self, app):
        if self._table is not None and self._selection != SelectionName.WATCH:
            app.layout.focus(self._table)

    def stop(self):
        try:
            self._exchange.unsubscribe(self._subscription_id)
        except AttributeError:
            logging.warning(
                "Tried to unsubscribe from exchange before "
                "subscription was activated."
            )

    def _set_selection(self, new_selection):
        self._selection = new_selection
        self._render()

    def _render(self):
        if self._selection in {SelectionName.UP, SelectionName.DOWN}:
            self._render_differences(self._differences, self._selection)
        else:
            self._render_watch()
        get_app().invalidate()

    def _render_local_mtime(self, difference):
        if difference.left is not None and difference.left.is_file():
            return naturaltime(difference.left.attrs.last_modified)
        return "-"

    def _render_remote_mtime(self, difference):
        if difference.right is not None and difference.right.is_file():
            return naturaltime(difference.right.attrs.last_modified)
        return "-"

    def _render_local_size(self, difference):
        if difference.left is not None and difference.left.is_file():
            return naturalsize(difference.left.attrs.size)
        return "-"

    def _render_remote_size(self, difference):
        if difference.right is not None and difference.right.is_file():
            return naturalsize(difference.right.attrs.size)
        return "-"

    def _render_help_box(self, text):
        text_area = TextArea(
            text, focusable=False, read_only=True, dont_extend_height=True
        )
        return to_container(text_area)

    def _render_watch(self):
        help_box = self._render_help_box(WATCH_HELP_TEXT)
        self.container.children = [Window(height=1), help_box, Window()]

    def _size_transferred(self, difference, direction):
        if (
            difference.difference_type == DifferenceType.LEFT_ONLY
            and difference.left.is_file()
        ):
            return difference.left.attrs.size
        elif (
            difference.difference_type == DifferenceType.RIGHT_ONLY
            and difference.right.is_file()
        ):
            return difference.right.attrs.size
        elif difference.difference_type in {
            DifferenceType.TYPE_DIFFERENT,
            DifferenceType.ATTRS_DIFFERENT,
        }:
            if direction == SelectionName.UP and difference.left.is_file():
                return difference.left.attrs.size
            elif (
                direction == SelectionName.DOWN and difference.right.is_file()
            ):
                return difference.right.attrs.size
            return 0
        return 0

    def _render_table(self, differences, direction):
        def sort_key(difference):
            """ Order first by action, then by size """
            text = ACTION_TEXT[(difference.difference_type, direction)]
            size = self._size_transferred(difference, direction)
            if "delete" in text:
                return (0, -size)
            elif "replace" in text:
                return (1, -size)
            else:
                return (2, -size)

        sorted_differences = sorted(differences, key=sort_key)

        paths = []
        actions = []
        local_mtimes = []
        remote_mtimes = []
        local_sizes = []
        remote_sizes = []

        for difference in sorted_differences:
            if difference.difference_type == DifferenceType.LEFT_ONLY:
                paths.append(difference.left.path)
            elif difference.difference_type == DifferenceType.RIGHT_ONLY:
                paths.append(difference.right.path)
            else:
                paths.append(difference.left.path)

            local_mtimes.append(self._render_local_mtime(difference))
            remote_mtimes.append(self._render_remote_mtime(difference))

            local_sizes.append(self._render_local_size(difference))
            remote_sizes.append(self._render_remote_size(difference))

            action = ACTION_TEXT[(difference.difference_type, direction)]
            actions.append(action)

        columns = [
            TableColumn(paths, "PATH"),
            TableColumn(actions, "ACTION"),
            TableColumn(
                local_mtimes,
                "LOCAL MTIME",
                ColumnSettings(alignment=Alignment.RIGHT),
            ),
            TableColumn(
                remote_mtimes,
                "REMOTE MTIME",
                ColumnSettings(alignment=Alignment.RIGHT),
            ),
            TableColumn(
                local_sizes,
                "LOCAL SIZE",
                ColumnSettings(alignment=Alignment.RIGHT),
            ),
            TableColumn(
                remote_sizes,
                "REMOTE SIZE",
                ColumnSettings(alignment=Alignment.RIGHT),
            ),
        ]
        table = Table(columns, sep="  ")
        return table

    def _render_differences(self, differences, direction):
        if not differences:
            help_box = self._render_help_box(FULLY_SYNCHRONIZED_HELP_TEXT)
            self.container.children = [Window(height=1), help_box, Window()]
        else:
            self._table = self._render_table(differences, direction)
            help_box = self._render_help_box(
                UP_SYNC_HELP_TEXT
                if direction == SelectionName.UP
                else DOWN_SYNC_HELP_TEXT
            )
            self.container.children = [
                Window(height=1),
                help_box,
                to_container(self._table),
            ]


class DifferencesScreen(BaseScreen):
    def __init__(self, differences, exchange):
        super().__init__()
        self._exchange = exchange
        self._bottom_toolbar = Window(
            FormattedTextControl(
                "[arrows] Navigation " "[r] Refresh  " "[?] Help  " "[q] Quit"
            ),
            height=1,
            style="reverse",
        )
        self._summary = Summary(exchange)
        self._details = Details(
            exchange, differences, self._summary.current_selection
        )
        self.bindings = KeyBindings()

        @self.bindings.add("d")  # noqa: F811
        def _(event):
            if self._summary.current_selection == SelectionName.DOWN:
                self._exchange.publish(Messages.SYNC_PLATFORM_TO_LOCAL)
            else:
                self._summary.current_selection = SelectionName.DOWN

        @self.bindings.add("u")  # noqa: F811
        def _(event):
            if self._summary.current_selection == SelectionName.UP:
                self._exchange.publish(Messages.SYNC_LOCAL_TO_PLATFORM)
            else:
                self._summary.current_selection = SelectionName.UP

        @self.bindings.add("r")  # noqa: F811
        def _(event):
            self._exchange.publish(Messages.REFRESH_DIFFERENCES)

        @self.bindings.add("w")  # noqa: F811
        def _(event):
            if self._summary.current_selection == SelectionName.WATCH:
                self._exchange.publish(Messages.START_WATCH_SYNC)
            else:
                self._summary.current_selection = SelectionName.WATCH

        @self.bindings.add("?")  # noqa: F811
        def _(event):
            self._toggle_help()

        @self.bindings.add("right")  # noqa: F811
        def _(event):
            self._details.gain_focus_if_possible(event.app)

        @self.bindings.add("left")  # noqa: F811
        def _(event):
            self._summary.gain_focus(event.app)

        self._screen_container = HSplit(
            [
                VSplit(
                    [
                        self._summary.container,
                        Window(width=1),
                        VerticalLine(),
                        Window(width=1),
                        self._details.container,
                    ]
                ),
                self._bottom_toolbar,
            ]
        )
        self.main_container = FloatContainer(self._screen_container, floats=[])

    def on_mount(self, app):
        self._summary.gain_focus(app)

    def stop(self):
        self._details.stop()

    def _toggle_help(self):
        if self.main_container.floats:
            self.main_container.floats = []
        else:
            help_container = help_modal(HELP_TITLE, HELP_TEXT)
            self.main_container.floats = [help_container]
