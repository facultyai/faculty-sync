
import collections
import threading
import time

from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout import HSplit
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.application.current import get_app

from ..pubsub import Messages
from ..models import ChangeEventType

from .loading import LoadingIndicator


class Loading(object):

    def __init__(self):
        self._loading_indicator = LoadingIndicator()
        self._control = FormattedTextControl('')
        self.container = HSplit([
            Window(height=1),
            Window(self._control, height=1),
            Window()
        ])
        self._thread = None
        self._stop_event = threading.Event()
        self._start_updating_loading_indicator()

    def _render(self):
        self._control.text = \
            '  {} Loading directory structure on SherlockML'.format(
                self._loading_indicator.current())

    def _start_updating_loading_indicator(self):
        def run():
            app = get_app()
            while not self._stop_event.is_set():
                self._loading_indicator.next()
                self._render()
                time.sleep(0.5)
                app.invalidate()
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()


class CurrentlySyncing(object):

    def __init__(self):
        self._current_event = None
        self._loading_indicator = LoadingIndicator()
        self._control = FormattedTextControl('')
        self.container = Window(self._control, height=1)
        self._stop_event = threading.Event()
        self._thread = None
        self._start_updating_loading_indicator()

    def set_current_event(self, fs_event):
        self._current_event = fs_event

    def stop(self):
        self._stop_event.set()

    def _render(self):
        if self._current_event is None:
            self._control.text = ''
        else:
            path = self._current_event.path
            self._control.text = '  {} {}'.format(
                self._loading_indicator.current(), path)

    def _start_updating_loading_indicator(self):
        def run():
            app = get_app()
            while not self._stop_event.is_set():
                self._loading_indicator.next()
                self._render()
                time.sleep(0.5)
                app.invalidate()
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()


class WatchSyncScreen(object):

    def __init__(self, exchange):
        self._exchange = exchange

        self._held_files = []
        self._recently_synced_items = collections.deque(maxlen=10)

        self._loading_component = Loading()
        self._currently_syncing_component = None
        self._recently_synced_items_control = FormattedTextControl('')
        self._held_files_control = FormattedTextControl('')

        self.menu_bar = Window(FormattedTextControl(
                '[s] Stop  '
                '[q] Quit'
            ), height=1, style='reverse')

        self.main_container = HSplit([
            self._loading_component.container,
            self.menu_bar
        ])
        self._exchange.subscribe(
            'START_WATCH_SYNC_MAIN_LOOP',
            lambda _: self._start_main_screen()
        )
        self._exchange.subscribe(
            Messages.HELD_FILES_CHANGED,
            lambda held_files: self._update_held_files(held_files)
        )
        self._exchange.subscribe(
            Messages.STARTING_HANDLING_FS_EVENT,
            lambda event: self._on_start_handling_fs_event(event)
        )
        self._exchange.subscribe(
            Messages.FINISHED_HANDLING_FS_EVENT,
            lambda event: self._on_finish_handling_fs_event(event)
        )

        self.bindings = KeyBindings()

        @self.bindings.add('s')
        def _(event):
            self._exchange.publish(Messages.STOP_WATCH_SYNC)

    def _stop_loading_component(self):
        if self._loading_component is not None:
            self._loading_component.stop()
            self._loading_component = None

    def _stop_main_components(self):
        if self._currently_syncing_component is not None:
            self._currently_syncing_component.stop()
            self._currently_syncing_component = None

    def _start_main_screen(self):
        self._stop_loading_component()
        self._currently_syncing_component = CurrentlySyncing()
        self._update_recently_synced_items_control()
        self._update_held_files_control()
        self.main_container.children = [
            Window(height=1),
            self._currently_syncing_component.container,
            Window(self._recently_synced_items_control, height=10),
            Window(char='-', height=1),
            Window(FormattedTextControl(
                'The following files will not be synced '
                'to avoid accidentally overwriting changes on SherlockML:'),
                dont_extend_height=True
            ),
            Window(self._held_files_control),
            self.menu_bar
        ]

    def _update_held_files(self, held_files):
        self._held_files = held_files
        self._update_held_files_control()

    def _on_start_handling_fs_event(self, fs_event):
        if self._currently_syncing_component:
            self._currently_syncing_component.set_current_event(fs_event)

    def _on_finish_handling_fs_event(self, fs_event):
        self._recently_synced_items.appendleft(fs_event)
        self._update_recently_synced_items_control()
        if self._currently_syncing_component:
            self._currently_syncing_component.set_current_event(None)

    def _update_recently_synced_items_control(self):
        recent_syncs_text = [
            '  {}'.format(self._format_fs_event(fs_event))
            for fs_event in self._recently_synced_items
        ]
        self._recently_synced_items_control.text = '\n'.join(recent_syncs_text)

    def _format_fs_event(self, event):
        if event.event_type == ChangeEventType.MOVED:
            src_path = event.path
            dest_path = event.extra_args['dest_path']
            event_str = '> {} -> {}'.format(src_path, dest_path)
        elif event.event_type == ChangeEventType.DELETED:
            event_str = 'x {}'.format(event.path)
        else:
            event_str = '> {}'.format(event.path)
        return event_str

    def _update_held_files_control(self):
        held_files_text = [
            '  x {}'.format(held_file) for held_file in self._held_files
        ]
        self._held_files_control.text = '\n'.join(held_files_text)

    def stop(self):
        pass
