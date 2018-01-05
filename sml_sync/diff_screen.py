
from enum import Enum

from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout import HSplit, VSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import Window

import inflect

from ..pubsub import Messages


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
        self._set_selection_index(0)

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
            difference[1].path for difference in differences
            if difference[0] == 'LEFT_ONLY'
        ]
        extra_remote_paths = [
            difference[1].path for difference in differences
            if difference[0] == 'RIGHT_ONLY'
        ]
        other_differences = [
            difference[1].path for difference in differences
            if difference[0] in {'TYPE_DIFFERENT', 'ATTRS_DIFFERENT'}
        ]
        if not extra_local_paths and not extra_remote_paths and not other_differences:
            self._has_differences = False
            self._menu_containers = [
                Window('  Local directory and SherlockML are synchronized.')
            ]
        else:
            self._has_differences = True
            if extra_local_paths:
                text = 'There {} {} {} that {} locally but not on SherlockML'.format(
                    self._plural_verb('is', len(extra_local_paths)),
                    len(extra_local_paths),
                    self._plural('file', len(extra_local_paths)),
                    self._plural_verb('exists', len(extra_local_paths))
                )
                container = Window(FormattedTextControl(text), height=1)
                self._menu_containers.append(container)
                self._menu_container_names.append(SummaryContainerName.LOCAL)
            if extra_remote_paths:
                text = 'There {} {} {} that {} only on SherlockML'.format(
                    self._plural_verb('is', len(extra_remote_paths)),
                    len(extra_remote_paths),
                    self._plural('file', len(extra_remote_paths)),
                    self._plural_verb('exists', len(extra_remote_paths))
                )
                container = Window(FormattedTextControl(text), height=1)
                self._menu_containers.append(container)
                self._menu_container_names.append(SummaryContainerName.REMOTE)
            if other_differences:
                text = 'There {} {} {} that {} not synchronized'.format(
                    self._plural_verb('is', len(other_differences)),
                    len(other_differences),
                    self._plural('file', len(other_differences)),
                    self._plural_verb('is', len(other_differences))
                )
                container = Window(FormattedTextControl(text), height=1)
                self._menu_containers.append(container)
                self._menu_container_names.append(SummaryContainerName.BOTH)


class Details(object):

    def __init__(self, differences, initial_focus):
        self._focus = initial_focus
        self._differences = differences
        self._control = FormattedTextControl('')
        self.container = Window(self._control)
        self._render()

    def set_focus(self, new_focus):
        self._focus = new_focus
        self._render()

    def _render(self):
        if self._focus is None:
            self._container = Window()
        elif self._focus == SummaryContainerName.LOCAL:
            paths = [
                difference[1].path
                for difference in self._differences
                if difference[0] == 'LEFT_ONLY'
            ]
            self._render_paths(paths)
        elif self._focus == SummaryContainerName.REMOTE:
            paths = [
                difference[1].path
                for difference in self._differences
                if difference[0] == 'RIGHT_ONLY'
            ]
            self._render_paths(paths)
        else:
            paths = [
                difference[1].path
                for difference in self._differences
                if difference[0] in {'TYPE_DIFFERENT', 'ATTRS_DIFFERENT'}
            ]
            self._render_paths(paths)

    def _render_paths(self, paths):
        path_texts = ['    {}'.format(path) for path in paths]
        self._control.text = '\n'.join(path_texts)


class DifferencesScreen(object):

    def __init__(self, differences, exchange):
        self._exchange = exchange
        self._bottom_toolbar = Window(FormattedTextControl(
            '[d] Sync SherlockML files down  '
            '[u] Sync local files up  '
            '[r] Refresh  '
            '[w] Continuous sync from local changes  '
            '[q] Quit'
        ), height=1, style='reverse')
        self._summary = Summary(differences)
        self._details = Details(differences, self._summary.current_focus)
        self.bindings = KeyBindings()

        @self.bindings.add('d')
        def _(event):
            self._exchange.publish(Messages.SYNC_SHERLOCKML_TO_LOCAL)

        @self.bindings.add('u')
        def _(event):
            self._exchange.publish(Messages.SYNC_LOCAL_TO_SHERLOCKML)

        @self.bindings.add('r')
        def _(event):
            self._exchange.publish(Messages.REFRESH_DIFFERENCES)

        @self.bindings.add('w')
        def _(event):
            self._exchange.publish(Messages.START_WATCH_SYNC)

        @self.bindings.add('tab')
        @self.bindings.add('down')
        @self.bindings.add('left')
        def _(event):
            new_focus = self._summary.focus_next()
            self._details.set_focus(new_focus)

        @self.bindings.add('s-tab')
        @self.bindings.add('up')
        @self.bindings.add('right')
        def _(event):
            new_focus = self._summary.focus_previous()
            self._details.set_focus(new_focus)

        self.main_container = HSplit(
            [Window(height=1)] +
            self._summary.containers +
            [Window(height=1), Window(char='-', height=1), Window(height=1)] +
            [self._details.container] +
            [self._bottom_toolbar]
        )
