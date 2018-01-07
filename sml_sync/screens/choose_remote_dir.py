
import os
import logging
import difflib
import threading
import time
from queue import Queue, Empty

from prompt_toolkit.layout.widgets import TextArea
from prompt_toolkit.layout import HSplit, VSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding.key_bindings import KeyBindings

from ..pubsub import Messages
from .loading import LoadingIndicator
from .base import BaseScreen


class Completions(object):

    def __init__(self):
        self._completions = None
        self._control = FormattedTextControl('')

        self._current_index = None
        self._margin_control = FormattedTextControl('')
        self._margin = Window(self._margin_control, width=2)
        self.container = VSplit([self._margin, Window(self._control)])

    def set_completions(self, completions):
        self._completions = completions
        self._current_index = 0 if completions else None
        self._render()

    def move_selection_down(self):
        if self._current_index is not None and self._completions is not None:
            self._current_index = (self._current_index + 1) % len(self._completions)
            self._render()

    def move_selection_up(self):
        if self._current_index is not None and self._completions is not None:
            self._current_index = (self._current_index - 1) % len(self._completions)
            self._render()

    def current_selection(self):
        if self._current_index is not None and self._completions is not None:
            return self._completions[self._current_index]

    def _render(self):
        if self._completions is None:
            self._control.text = ''
        else:
            self._control.text = '\n'.join(self._completions)
            margin_lines = []
            for icompletion in range(len(self._completions)):
                margin_lines.append(
                    '> ' if icompletion == self._current_index
                    else (' ' * 2)
                )
            margin_text = '\n'.join(margin_lines)
            self._margin_control.text = margin_text


class AsyncCompleterStatus(object):

    def __init__(self):
        self._loading_indicator = LoadingIndicator()
        self._status = 'IDLE'
        self._current_path = None
        self._control = FormattedTextControl()
        self.container = HSplit([
            Window(height=1),
            Window(self._control, height=1)
        ], height=2)
        self._thread = None
        self._stop_event = threading.Event()
        self._start_updating_loading_indicator()

    def _render(self):
        if self._status == 'IDLE':
            self._control.text = ''
        else:
            if self._current_path is not None:
                self._control.text = (
                    '{} Fetching subdirectories of {}'.format(
                        self._loading_indicator.current(), self._current_path)
                    )
            else:
                self._control.text = self._loading_indicator.current()

    def set_status(self, status, current_path=None):
        self._status = status
        self._current_path = current_path
        self._render()

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


class AsyncCompleter(object):

    def __init__(self, exchange, get_paths_in_directory):
        self._exchange = exchange
        self._queue = Queue()
        self._get_paths_in_directory = get_paths_in_directory
        self._completions_cache = {}
        self._stop_event = threading.Event()
        self.current_status = 'IDLE'
        self.start()

    def cache_completions(self, directory):
        self._queue.put(directory)

    def get_subdirectories(self, directory):
        return self._completions_cache.get(directory)

    def start(self):
        def run():
            while not self._stop_event.is_set():
                try:
                    path = self._queue.get(timeout=0.1)
                    if path not in self._completions_cache:
                        # path has not been fetched already
                        logging.info(
                            'Retrieving completions for {}'.format(path))
                        self.current_status = 'BUSY'
                        self._exchange.publish(
                            Messages.SUBDIRECTORY_WALKER_STATUS_CHANGE, path)
                        try:
                            subdirectories = self._get_paths_in_directory(path)
                            self._completions_cache[path] = subdirectories
                            self._exchange.publish(
                                Messages.NEW_SUBDIRECTORIES_WALKED)
                        except Exception:
                            logging.exception(
                                'Error fetching subdirectories of {}'.format(
                                    path))
                except Empty:
                    if self.current_status != 'IDLE':
                        self.current_status = 'IDLE'
                        self._exchange.publish(
                            Messages.SUBDIRECTORY_WALKER_STATUS_CHANGE)
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()


class RemoteDirectoryPromptScreen(BaseScreen):

    def __init__(self, exchange, get_paths_in_directory):
        super().__init__()
        self.use_default_bindings = False
        self._exchange = exchange

        self._input = TextArea(text='/project/', multiline=False)
        self._buffer = self._input.buffer
        self._buffer.cursor_position = len(self._buffer.text)
        self._completions_component = Completions()
        self._completer = AsyncCompleter(exchange, get_paths_in_directory)
        self._completer_status_component = AsyncCompleterStatus()
        self._bottom_toolbar = Window(FormattedTextControl(
            '[tab] Enter selected directory  '
            '[return] Choose selected directory  '
            '[arrows] Navigation  '
            '[C-c] Quit'
        ), height=1, style='reverse')
        self._container = HSplit([
            Window(height=1),
            Window(
                FormattedTextControl(
                    'Choose directory to synchronize to on SherlockML: '
                ),
                height=1
            ),
            self._input,
            Window(height=1),
            self._completions_component.container,
            self._completer_status_component.container,
        ])
        self.main_container = HSplit([
            VSplit([Window(width=2), self._container]),
            self._bottom_toolbar
        ])
        self._buffer.on_text_changed += self._handle_text_changed

        self.bindings = KeyBindings()

        @self.bindings.add('down')
        def _(event):
            self._completions_component.move_selection_down()

        @self.bindings.add('up')
        def _(event):
            self._completions_component.move_selection_up()

        @self.bindings.add('tab')
        def _(event):
            current_selection = self._completions_component.current_selection()
            if current_selection is not None:
                self._buffer.cursor_position = 0
                self._buffer.text = current_selection + '/'
                self._buffer.cursor_position = len(self._buffer.text)

        @self.bindings.add('enter')
        def _(event):
            current_selection = self._completions_component.current_selection()
            self._exchange.publish(
                Messages.VERIFY_REMOTE_DIRECTORY,
                current_selection
            )

        @self.bindings.add('c-c')
        def _(event):
            self._exchange.publish(Messages.STOP_CALLED)

        self._exchange.subscribe(
            Messages.NEW_SUBDIRECTORIES_WALKED,
            lambda _: self._handle_text_changed()
        )
        self._exchange.subscribe(
            Messages.SUBDIRECTORY_WALKER_STATUS_CHANGE,
            lambda path: self._handle_walker_status_change(path)
        )

    def on_mount(self, app):
        app.layout.focus(self.main_container)
        self._handle_text_changed()

    def _handle_text_changed(self, _=None):
        current_text = self._buffer.text
        directory = os.path.dirname(current_text)
        subdirectories = self._completer.get_subdirectories(directory)
        if subdirectories is None:
            self._completer.cache_completions(directory)
        else:
            current_basename = os.path.basename(current_text)
            remote_basenames = {
                os.path.basename(os.path.normpath(subdirectory)): subdirectory
                for subdirectory in subdirectories
            }
            matching_basenames = difflib.get_close_matches(
                current_basename,
                remote_basenames.keys(),
                cutoff=0.0,
                n=20
            )
            matching_subdirectories = [
                remote_basenames[basename]
                for basename in matching_basenames
            ]
            completions = [directory] + matching_subdirectories
            self._completions_component.set_completions(completions)

    def _handle_walker_status_change(self, path):
        self._completer_status_component.set_status(
            self._completer.current_status, path)

