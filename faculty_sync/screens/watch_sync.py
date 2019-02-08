import collections
import threading
import time
from datetime import datetime

from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, VSplit
from prompt_toolkit.layout.containers import FloatContainer, Window
from prompt_toolkit.layout.controls import FormattedTextControl

from . import humanize
from ..models import ChangeEventType
from ..pubsub import Messages
from .base import BaseScreen
from .help import help_modal
from .loading import LoadingIndicator

HELP_TITLE = "Incremental synchronization"

HELP_TEXT = """\
A background process is currently watching the local directory. When
it detects a change, that change is replicated in the directory in
Faculty Platform.

To avoid overwriting changes that you may have made on Faculty Platform
directly, we avoid pushing changes if the file is modified on
Faculty Platform while this process is running.

Keys:

    [s] Stop incremental synchronization and go back to main screen
    [d] Bring all the changes down from Faculty Platform. This only updates
        files that are newer on Faculty Platform than locally. It will not
        delete local files that do not exist on Faculty Platform.
    [q] Quit the application
    [?] Toggle this message
"""


class Loading(object):
    def __init__(self):
        self._loading_indicator = LoadingIndicator()
        self._control = FormattedTextControl("")
        self.container = HSplit(
            [Window(height=1), Window(self._control, height=1), Window()]
        )
        self._thread = None
        self._stop_event = threading.Event()
        self._start_updating_loading_indicator()

    def _render(self):
        self._control.text = "  {} Loading directory structure on Faculty".format(
            self._loading_indicator.current()
        )

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
        self._has_synced_at_least_once = False
        self._control = FormattedTextControl("")
        self.container = Window(self._control, height=1)
        self._stop_event = threading.Event()
        self._thread = None
        self._start_updating_loading_indicator()

    def set_current_event(self, fs_event):
        self._has_synced_at_least_once = True
        self._current_event = fs_event

    def stop(self):
        self._stop_event.set()

    def _render(self):
        if self._current_event is None and not self._has_synced_at_least_once:
            self._control.text = "  Ready and waiting for local changes"
        elif self._current_event is None:
            self._control.text = ""
        else:
            path = self._current_event.path
            self._control.text = "  {} {}".format(
                self._loading_indicator.current(), path
            )

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


class RecentlySyncedItems(object):
    def __init__(self):
        self._items = collections.deque(maxlen=10)
        self._empty_window = Window(height=1)
        self.container = VSplit([self._empty_window])
        self._thread = None
        self._stop_event = threading.Event()
        self._start_updating()

    def add_item(self, fs_event):
        self._items.appendleft((datetime.now(), fs_event))
        self._render()

    def stop(self):
        self._stop_event.set()

    def _render(self):
        items = list(self._items)  # Defensive copy to avoid race conditions
        if items:
            events = [event for (_, event) in items]
            times = [sync_time for (sync_time, _) in items]
            self.container.children = [
                Window(width=4, height=len(items)),
                self._render_events(events),
                Window(width=2, height=len(items)),
                self._render_times(times),
            ]
        else:
            self.container.children = [self._empty_window]

    def _render_events(self, events):
        event_texts = [self._format_event(event) for event in events]
        event_max_width = max(len(event_text) for event_text in event_texts)
        return Window(
            FormattedTextControl("\n".join(event_texts)),
            width=min(event_max_width, 50),
            height=len(events),
        )

    def _format_event(self, event):
        src_path = event.path
        src_path_text = self._format_path(src_path, event.is_directory)
        if event.event_type == ChangeEventType.MOVED:
            dest_path = event.extra_args["dest_path"]
            dest_path_text = self._format_path(dest_path, event.is_directory)
            event_text = "{} -> {}".format(src_path_text, dest_path_text)
        elif event.event_type == ChangeEventType.DELETED:
            event_text = "{} (x)".format(src_path_text)
        else:
            event_text = "{}".format(src_path_text)
        return event_text

    def _format_path(self, path, is_directory):
        if is_directory:
            return path.rstrip("/") + "/"
        else:
            return path

    def _render_times(self, times):
        times_text = [humanize.naturaltime(t) for t in times]
        return Window(
            FormattedTextControl("\n".join(times_text)), height=len(times)
        )

    def _start_updating(self):
        def run():
            app = get_app()
            while not self._stop_event.is_set():
                self._render()
                time.sleep(5)
                app.invalidate()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()


class HeldFiles(object):
    def __init__(self):
        self._held_paths = []
        self.container = HSplit([Window()])

    def set_paths(self, paths):
        # Truncate to avoid huge list lengths
        self._held_paths = list(paths)[:100]
        self._render()

    def _render(self):
        if self._held_paths:
            self.container.children = [
                Window(height=1),
                Window(char="-", height=1),
                Window(height=1),
                Window(
                    FormattedTextControl(
                        "  The following files will not be synced to "
                        "avoid accidentally overwriting changes on Faculty:"
                    ),
                    dont_extend_height=True,
                ),
                Window(height=1),
                self._format_held_paths(self._held_paths),
            ]
        else:
            self.container.children = Window(dont_extend_height=True)

    def _format_held_paths(self, paths):
        paths_text = "\n".join(["    {}".format(path) for path in paths])
        control = FormattedTextControl(paths_text)
        return Window(control)


class WatchSyncScreen(BaseScreen):
    def __init__(self, exchange):
        super().__init__()
        self._exchange = exchange

        self._loading_component = Loading()
        self._currently_syncing_component = None
        self._recently_synced_component = None
        self._held_files_component = None

        self.menu_bar = Window(
            FormattedTextControl(
                "[s] Stop  [d] Sync files down  [q] Quit  [?] Help"
            ),
            height=1,
            style="reverse",
        )

        self._screen_container = HSplit(
            [self._loading_component.container, self.menu_bar]
        )

        self.main_container = FloatContainer(self._screen_container, floats=[])

        self._subscription_ids = [
            self._exchange.subscribe(
                Messages.START_WATCH_SYNC_MAIN_LOOP,
                lambda _: self._start_main_screen(),
            ),
            self._exchange.subscribe(
                Messages.HELD_FILES_CHANGED,
                lambda held_files: self._update_held_files(held_files),
            ),
            self._exchange.subscribe(
                Messages.STARTING_HANDLING_FS_EVENT,
                lambda event: self._on_start_handling_fs_event(event),
            ),
            self._exchange.subscribe(
                Messages.FINISHED_HANDLING_FS_EVENT,
                lambda event: self._on_finish_handling_fs_event(event),
            ),
        ]

        self.bindings = KeyBindings()

        @self.bindings.add("s")
        def _(event):
            self._exchange.publish(Messages.STOP_WATCH_SYNC)

        @self.bindings.add("d")
        def _(event):
            self._exchange.publish(Messages.DOWN_IN_WATCH_SYNC)

        @self.bindings.add("?")
        def _(event):
            self._toggle_help()

    def _stop_loading_component(self):
        if self._loading_component is not None:
            self._loading_component.stop()
            self._loading_component = None

    def _stop_main_components(self):
        if self._currently_syncing_component is not None:
            self._currently_syncing_component.stop()
            self._currently_syncing_component = None
        if self._recently_synced_component is not None:
            self._recently_synced_component.stop()
            self._recently_synced_component = None

    def _start_main_screen(self):
        self._stop_loading_component()
        self._currently_syncing_component = CurrentlySyncing()
        self._recently_synced_component = RecentlySyncedItems()
        self._held_files_component = HeldFiles()
        self._screen_container.children = [
            Window(height=1),
            self._currently_syncing_component.container,
            self._recently_synced_component.container,
            self._held_files_component.container,
            self.menu_bar,
        ]

    def _update_held_files(self, held_files):
        if self._held_files_component:
            self._held_files_component.set_paths(held_files)

    def _on_start_handling_fs_event(self, fs_event):
        if self._currently_syncing_component:
            self._currently_syncing_component.set_current_event(fs_event)

    def _on_finish_handling_fs_event(self, fs_event):
        if self._recently_synced_component:
            self._recently_synced_component.add_item(fs_event)
        if self._currently_syncing_component:
            self._currently_syncing_component.set_current_event(None)

    def stop(self):
        self._stop_main_components()
        for subscription_id in self._subscription_ids:
            self._exchange.unsubscribe(subscription_id)

    def _toggle_help(self):
        if self.main_container.floats:
            self.main_container.floats = []
        else:
            help_container = help_modal(HELP_TITLE, HELP_TEXT)
            self.main_container.floats = [help_container]
