
import collections
import threading
import traceback

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding.key_bindings import (
    KeyBindings, merge_key_bindings
)
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl

from .pubsub import Messages
from .models import ChangeEventType


class View(object):

    def __init__(self, configuration, exchange):
        self.configuration = configuration
        self.exchange = exchange

        self.main_container = Window(FormattedTextControl(''))
        self.top_toolbar = self._render_top_toolbar()
        self.bindings = self._create_bindings()

        self.root_container = HSplit([
            self.top_toolbar,
            self.main_container
        ])

        self.layout = Layout(
            container=self.root_container
        )

        self.application = Application(
            layout=self.layout,
            key_bindings=self.bindings,
            full_screen=True
        )

    def mount(self, screen):
        """
        Mount a screen into the view.

        The screen must have a `main_container` attribute and,
        optionally, a `bindings` attribute.
        """
        root_container = HSplit([
            self.top_toolbar,
            screen.main_container
        ])
        self.layout.container = root_container
        try:
            merged_key_bindings = merge_key_bindings([
                self.bindings, screen.bindings
            ])
            self.application.key_bindings = merged_key_bindings
        except AttributeError:
            # Screen does not define additional keybindings
            self.application.key_bindings = self.bindings
            pass

    def start(self):
        def run():
            try:
                self.application.run()
            except Exception as e:
                traceback.print_exc()
                print(e)
        self._thread = threading.Thread(target=run)
        self._thread.start()

    def stop(self):
        if self.application.is_running:
            self.application.set_result(None)

    def _render_top_toolbar(self):
        top_text = (
            'SherlockML synchronizer '
            '{configuration.local_dir} -> '
            '{configuration.project_id}:{configuration.remote_dir}'
        ).format(configuration=self.configuration)
        top_toolbar = Window(
            FormattedTextControl(top_text),
            height=1,
            style='reverse'
        )
        return top_toolbar

    def _create_bindings(self):
        bindings = KeyBindings()

        @bindings.add('c-c')
        @bindings.add('q')
        def _(event):
            self.exchange.publish('STOP_CALLED')

        return bindings


class WalkingFileTreesScreen(object):

    def __init__(self, initial_status, exchange):
        self.status_control = FormattedTextControl('')
        self.set_status(initial_status)
        self.main_container = HSplit([Window(self.status_control)])
        self._exchange = exchange
        self._subscription_id = exchange.subscribe(
            'WALK_STATUS_CHANGE',
            lambda new_status: self.set_status(new_status)
        )

    def set_status(self, status):
        if status == 'CONNECTING':
            self.status_control.text = 'Connecting to SherlockML server'
        elif status == 'LOCAL_WALK':
            self.status_control.text = 'Walking local file tree'
        elif status == 'REMOTE_WALK':
            self.status_control.text = 'Walking file tree on SherlockML'
        elif status == 'CALCULATING_DIFFERENCES':
            self.status_control.text = (
                'Calculating differences between local and remote file trees')

    def stop(self):
        self._exchange.unsubscribe(self._subscription_id)


class SynchronizationScreen(object):

    def __init__(self):
        self.main_container = Window(
            FormattedTextControl('Synchronizing'))


class WatchSyncScreen(object):

    def __init__(self, exchange):
        self._exchange = exchange

        self._held_files = []
        self._recently_synced_items = collections.deque(maxlen=10)
        self._current_event = None

        self._loading_status_control = FormattedTextControl('Loading...')
        self._queue_status_control = FormattedTextControl('')
        self._recently_synced_items_control = FormattedTextControl('')
        self._held_files_control = FormattedTextControl('')

        self.menu_bar = Window(FormattedTextControl(
                '[s] Stop  '
                '[q] Quit'
            ), height=1, style='reverse')

        self.main_container = HSplit([
            Window(self._loading_status_control),
            self.menu_bar
        ])
        self._exchange.subscribe(
            'START_WATCH_SYNC_MAIN_LOOP',
            lambda _: self._update_main_screen()
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

    def _update_main_screen(self):
        self._update_recently_synced_items_control()
        self._update_held_files_control()
        self.main_container.children = [
            Window(self._queue_status_control, height=1),
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
        self._current_event = fs_event
        self._update_queue_status()

    def _on_finish_handling_fs_event(self, fs_event):
        self._current_event = None
        self._recently_synced_items.appendleft(fs_event)
        self._update_queue_status()
        self._update_recently_synced_items_control()

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

    def _update_queue_status(self):
        if self._current_event is not None:
            path = self._current_event.path
            self._queue_status_control.text = '>>> {}'.format(path)
        else:
            self._queue_status_control.text = ''

    def _update_held_files_control(self):
        held_files_text = [
            '  x {}'.format(held_file) for held_file in self._held_files
        ]
        self._held_files_control.text = '\n'.join(held_files_text)

    def stop(self):
        pass
