
from enum import Enum

from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, VSplit, to_container
from prompt_toolkit.layout.containers import FloatContainer, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea

from ..pubsub import Messages
from ..models import DifferenceType
from .base import BaseScreen
from .help import help_modal
from .components import Table, TableColumn, VerticalMenu, MenuEntry
from .humanize import naturaltime, naturalsize
from . import styles

HELP_TITLE = 'Differences between local directory and SherlockML'

HELP_TEXT = """\
This is a summary of the differences between SherlockML and
your local directory. It summarizes the files that exist
only on SherlockML, the files that exist on locally and the
files that are on both, but with different modification times.

Keys:

    [u] Push all the local changes to SherlockML. This will
        erase any file that is on SherlockML, but not available
        locally.
    [d] Bring all the changes down from SherlockML. This will
        erase any file that is present locally but not on
        SherlockML.
    [r] Refresh differences between the local file system
        and SherlockML.
    [w] Enter incremental synchronization mode, where changes
        to the local file system are automatically replicated
        on SherlockML.
    [q] Quit the application.
    [?] Toggle this message.
"""

UP_SYNC_HELP_TEXT = """\
Press [u] to modify the SherlockML workspace so that it mirrors your local disk.

This will make the following changes to your SherlockML workspace:
"""

DOWN_SYNC_HELP_TEXT = """\
Press [d] to modify your local filesystem so that it mirrors the SherlockML workspace.

This will make the following changes to your local disk:
"""

WATCH_HELP_TEXT = """\
Press [w] to enter `watch` mode. Any time you save, move or delete a file, the change is automatically replicated on SherlockML.
"""

FULLY_SYNCHRONIZED_HELP_TEXT = """\
Your local disk and the SherlockML workspace are fully synchronized.
"""


class SelectionName(Enum):
    UP = 'UP'
    DOWN = 'DOWN'
    WATCH = 'WATCH'


class DiffScreenMessages(Enum):
    """
    Messages used internally in the differences screen
    """
    SELECTION_UPDATED = 'SELECTION_UPDATED'


class Summary(object):

    def __init__(self, exchange):
        self._exchange = exchange
        self._current_index = 0
        self._menu_container = VerticalMenu([
            MenuEntry(SelectionName.UP, 'Up'),
            MenuEntry(SelectionName.DOWN, 'Down'),
            MenuEntry(SelectionName.WATCH, 'Watch'),
        ], width=10)
        self._menu_container.register_menu_change_callback(
            lambda new_selection: self._on_new_selection(new_selection)
        )
        self.container = VSplit([
            Window(width=1),
            HSplit([
                Window(height=1),
                self._menu_container,
                Window()
            ])
        ])

    @property
    def current_selection(self):
        return self._menu_container.current_selection

    def gain_focus(self, app):
        app.layout.focus(self._menu_container)

    def _on_new_selection(self, new_selection):
        self._exchange.publish(
            DiffScreenMessages.SELECTION_UPDATED, new_selection)


class Details(object):

    def __init__(self, exchange, differences, initial_selection):
        self._selection = initial_selection
        self._differences = differences
        self._table = None
        self.container = HSplit([])

        self._render()

        exchange.subscribe(
            DiffScreenMessages.SELECTION_UPDATED,
            self._set_selection
        )

    def gain_focus(self, app):
        app.layout.focus(self._table)

    def _set_selection(self, new_selection):
        self._selection = new_selection
        self._render()

    def _render(self):
        if self._selection in {SelectionName.UP, SelectionName.DOWN}:
            self._render_differences(self._differences, self._selection.name)
        else:
            self._render_watch()
        get_app().invalidate()

    def _render_local_mtime(self, difference):
        if difference.left is not None and difference.left.is_file():
            return naturaltime(difference.left.attrs.last_modified)
        return ''

    def _render_remote_mtime(self, difference):
        if difference.right is not None and difference.right.is_file():
            return naturaltime(difference.right.attrs.last_modified)
        return ''

    def _render_local_size(self, difference):
        if difference.left is not None and difference.left.is_file():
            return naturalsize(difference.left.attrs.size)
        return ''

    def _render_remote_size(self, difference):
        if difference.right is not None and difference.right.is_file():
            return naturalsize(difference.right.attrs.size)
        return ''

    def _render_help_box(self, text):
        text_area = TextArea(
            text, focusable=False, read_only=True, dont_extend_height=True)
        return to_container(text_area)

    def _render_watch(self):
        help_box = self._render_help_box(WATCH_HELP_TEXT)
        self.container.children = [Window(height=1), help_box, Window()]

    def _render_table(self, differences, direction):
        action_map = {
            (DifferenceType.LEFT_ONLY, 'UP'): 'create remote',
            (DifferenceType.RIGHT_ONLY, 'DOWN'): 'create local',
            (DifferenceType.LEFT_ONLY, 'DOWN'): 'delete local',
            (DifferenceType.RIGHT_ONLY, 'UP'): 'delete remote',
            (DifferenceType.TYPE_DIFFERENT, 'UP'): 'replace remote',
            (DifferenceType.TYPE_DIFFERENT, 'DOWN'): 'replace local',
            (DifferenceType.ATTRS_DIFFERENT, 'UP'): 'replace remote',
            (DifferenceType.ATTRS_DIFFERENT, 'DOWN'): 'replace local'
        }
        paths = []
        actions = []
        local_mtimes = []
        remote_mtimes = []
        local_sizes = []
        remote_sizes = []

        for difference in differences:
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

            action = action_map[(difference.difference_type, direction)]
            actions.append(action)

        columns = [
            TableColumn(paths, 'PATH'),
            TableColumn(actions, 'ACTION'),
            TableColumn(local_mtimes, 'LOCAL MTIME'),
            TableColumn(remote_mtimes, 'REMOTE MTIME'),
            TableColumn(local_sizes, 'LOCAL SIZE'),
            TableColumn(remote_sizes, 'REMOTE SIZE'),
        ]
        table = Table(columns)
        return table

    def _render_differences(self, differences, direction):
        if not differences:
            help_box = self._render_help_box(FULLY_SYNCHRONIZED_HELP_TEXT)
            self.container.children = [Window(height=1), help_box, Window()]
        else:
            self._table = self._render_table(differences, direction)
            help_box = self._render_help_box(
                UP_SYNC_HELP_TEXT if direction == 'UP' else DOWN_SYNC_HELP_TEXT
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
        self._bottom_toolbar = Window(FormattedTextControl(
            '[d] Sync SherlockML files down  '
            '[u] Sync local files up  '
            '[r] Refresh  '
            '[w] Incremental sync from local changes\n'
            '[?] Help  '
            '[q] Quit'
        ), height=2, style='reverse')
        self._summary = Summary(exchange)
        self._details = Details(
            exchange, differences, self._summary.current_selection)
        self.bindings = KeyBindings()

        @self.bindings.add('d')  # noqa: F811
        def _(event):
            if self._summary.current_selection == SelectionName.DOWN:
                self._exchange.publish(Messages.SYNC_SHERLOCKML_TO_LOCAL)

        @self.bindings.add('u')  # noqa: F811
        def _(event):
            if self._summary.current_selection == SelectionName.UP:
                self._exchange.publish(Messages.SYNC_LOCAL_TO_SHERLOCKML)

        @self.bindings.add('r')  # noqa: F811
        def _(event):
            self._exchange.publish(Messages.REFRESH_DIFFERENCES)

        @self.bindings.add('w')  # noqa: F811
        def _(event):
            if self._summary.current_selection == SelectionName.WATCH:
                self._exchange.publish(Messages.START_WATCH_SYNC)

        @self.bindings.add('?')  # noqa: F811
        def _(event):
            self._toggle_help()

        @self.bindings.add('right')  # noqa: F811
        def _(event):
            self._details.gain_focus(event.app)

        @self.bindings.add('left')  # noqa: F811
        def _(event):
            self._summary.gain_focus(event.app)

        self._screen_container = HSplit([
            VSplit([
                self._summary.container,
                Window(width=1),
                Window(width=1, char=styles.get_vertical_border_char()),
                Window(width=1),
                self._details.container
            ]),
            self._bottom_toolbar
        ])
        self.main_container = FloatContainer(
            self._screen_container,
            floats=[]
        )

    def on_mount(self, app):
        self._summary.gain_focus(app)

    def _toggle_help(self):
        if self.main_container.floats:
            self.main_container.floats = []
        else:
            help_container = help_modal(HELP_TITLE, HELP_TEXT)
            self.main_container.floats = [help_container]
