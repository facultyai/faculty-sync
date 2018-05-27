
from enum import Enum

import inflect
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, VSplit, to_container
from prompt_toolkit.layout.containers import FloatContainer, Window
from prompt_toolkit.layout.controls import FormattedTextControl

from ..pubsub import Messages
from ..models import DifferenceType
from .base import BaseScreen
from .help import help_modal
from .components import Table, TableColumn

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


class SummaryContainerName(Enum):
    LOCAL = 'LOCAL'
    REMOTE = 'REMOTE'
    BOTH = 'BOTH'


class Summary(object):

    def __init__(self, differences):
        self._differences = differences
        self._has_differences = False
        self._current_index = None
        self._menu_containers = []
        self._menu_container_names = []
        self._margin_control = FormattedTextControl('')
        self._margin = Window(self._margin_control, width=4)

        self._inflect = inflect.engine()
        self._plural = self._inflect.plural
        self._plural_verb = self._inflect.plural_verb

        self._render_containers(differences)

    @property
    def current_focus(self):
        if self._has_differences:
            return self._menu_container_names[self._current_index]
        else:
            return None

    @property
    def containers(self):
        return [VSplit([self._margin, HSplit(self._menu_containers)])]

    def focus_next(self):
        if self._has_differences:
            return self._set_selection_index(self._current_index + 1)

    def focus_previous(self):
        if self._has_differences:
            return self._set_selection_index(self._current_index - 1)

    def _set_selection_index(self, new_index):
        if self._has_differences:
            # Wrap around when selecting
            self._current_index = new_index % len(self._menu_containers)
            margin_lines = []
            for icontainer in range(len(self._menu_containers)):
                margin_lines.append(
                    '  > ' if icontainer == self._current_index
                    else (' ' * 4)
                )
            margin_text = '\n'.join(margin_lines)
            self._margin_control.text = margin_text
            return self._menu_container_names[self._current_index]

    def _render_containers(self, differences):
        extra_local_paths = [
            difference.left.path for difference in differences
            if difference.difference_type == DifferenceType.LEFT_ONLY
        ]
        extra_remote_paths = [
            difference.right.path for difference in differences
            if difference.difference_type == DifferenceType.RIGHT_ONLY
        ]
        other_differences = [
            difference.left.path for difference in differences
            if difference.difference_type in
            {DifferenceType.TYPE_DIFFERENT, DifferenceType.ATTRS_DIFFERENT}
        ]
        are_synchronized = (
            not extra_local_paths
            and not extra_remote_paths
            and not other_differences
        )
        if are_synchronized:
                self._has_differences = False
                self._menu_containers = [
                    Window(
                        FormattedTextControl(
                            'Local directory and SherlockML are synchronized.'
                        ),
                        height=1)
                ]
        else:
            self._has_differences = True
            if extra_local_paths:
                template = \
                    'There {} {} {} that {} locally but not on SherlockML'
                text = template.format(
                    self._plural_verb('is', len(extra_local_paths)),
                    len(extra_local_paths),
                    self._plural('file', len(extra_local_paths)),
                    self._plural_verb('exists', len(extra_local_paths))
                )
                container = Window(FormattedTextControl(text), height=1)
                self._menu_containers.append(container)
                self._menu_container_names.append(SummaryContainerName.LOCAL)
            if extra_remote_paths:
                template = 'There {} {} {} that {} only on SherlockML'
                text = template.format(
                    self._plural_verb('is', len(extra_remote_paths)),
                    len(extra_remote_paths),
                    self._plural('file', len(extra_remote_paths)),
                    self._plural_verb('exists', len(extra_remote_paths))
                )
                container = Window(FormattedTextControl(text), height=1)
                self._menu_containers.append(container)
                self._menu_container_names.append(SummaryContainerName.REMOTE)
            if other_differences:
                template = 'There {} {} {} that {} not synchronized'
                text = template.format(
                    self._plural_verb('is', len(other_differences)),
                    len(other_differences),
                    self._plural('file', len(other_differences)),
                    self._plural_verb('is', len(other_differences))
                )
                container = Window(FormattedTextControl(text), height=1)
                self._menu_containers.append(container)
                self._menu_container_names.append(SummaryContainerName.BOTH)
            self._set_selection_index(0)


class Details(object):

    def __init__(self, differences, initial_focus):
        self._focus = initial_focus
        self._differences = differences
        self.container = VSplit([Window(FormattedTextControl('Loading...'))])

        self._render()

    def set_focus(self, new_focus):
        self._focus = new_focus
        self._render()

    def _render(self):
        if self._focus is None:
            self.container.children = []
        elif self._focus == SummaryContainerName.LOCAL:
            file_objects = [
                difference.left
                for difference in self._differences
                if difference.difference_type == DifferenceType.LEFT_ONLY
            ]
            self._render_differences(file_objects)
        elif self._focus == SummaryContainerName.REMOTE:
            file_objects = [
                difference.right
                for difference in self._differences
                if difference.difference_type == DifferenceType.RIGHT_ONLY
            ]
            self._render_differences(file_objects)
        else:
            file_objects = [
                difference.left
                for difference in self._differences
                if difference.difference_type in
                {DifferenceType.TYPE_DIFFERENT, DifferenceType.ATTRS_DIFFERENT}
            ]
            self._render_differences(file_objects)

    def _render_differences(self, file_objects):
        file_paths = [file_object.path for file_object in file_objects]
        file_sizes = [
            str(file_object.attrs.size) if file_object.is_file() else ''
            for file_object in file_objects
        ]
        file_mtimes = [
            str(file_object.attrs.last_modified)
            if file_object.is_file() else ''
            for file_object in file_objects
        ]
        columns = [
            TableColumn(file_paths, 'PATH'),
            TableColumn(file_sizes, 'SIZE'),
            TableColumn(file_mtimes, 'LAST MODIFIED')
        ]
        self.container.children = [to_container(Table(columns))]


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
        self._summary = Summary(differences)
        self._details = Details(differences, self._summary.current_focus)
        self.bindings = KeyBindings()

        @self.bindings.add('d')  # noqa: F811
        def _(event):
            self._exchange.publish(Messages.SYNC_SHERLOCKML_TO_LOCAL)

        @self.bindings.add('u')  # noqa: F811
        def _(event):
            self._exchange.publish(Messages.SYNC_LOCAL_TO_SHERLOCKML)

        @self.bindings.add('r')  # noqa: F811
        def _(event):
            self._exchange.publish(Messages.REFRESH_DIFFERENCES)

        @self.bindings.add('w')  # noqa: F811
        def _(event):
            self._exchange.publish(Messages.START_WATCH_SYNC)

        @self.bindings.add('?')  # noqa: F811
        def _(event):
            self._toggle_help()

        @self.bindings.add('tab')  # noqa: F811
        @self.bindings.add('down')
        @self.bindings.add('left')
        def _(event):
            new_focus = self._summary.focus_next()
            self._details.set_focus(new_focus)

        @self.bindings.add('s-tab')  # noqa: F811
        @self.bindings.add('up')
        @self.bindings.add('right')
        def _(event):
            new_focus = self._summary.focus_previous()
            self._details.set_focus(new_focus)

        self._screen_container = HSplit(
            [Window(height=1)] +
            self._summary.containers +
            [Window(height=1), Window(char='-', height=1), Window(height=1)] +
            [self._details.container] +
            [self._bottom_toolbar]
        )
        self.main_container = FloatContainer(
            self._screen_container,
            floats=[]
        )

    def _toggle_help(self):
        if self.main_container.floats:
            self.main_container.floats = []
        else:
            help_container = help_modal(HELP_TITLE, HELP_TEXT)
            self.main_container.floats = [help_container]
