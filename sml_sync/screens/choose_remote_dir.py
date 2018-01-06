
import os
import logging
import difflib
import threading
import time

from prompt_toolkit.layout.widgets import TextArea
from prompt_toolkit.layout import HSplit, VSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.application.current import get_app


from .loading import LoadingIndicator


class Completions(object):

    def __init__(self):
        self._completions = None
        self._is_loading = True
        self._control = FormattedTextControl('')
        self._loading_indicator = LoadingIndicator()
        self._thread = None
        self._stop_event = threading.Event()
        self.container = Window(self._control)

    def set_loading(self):
        self._is_loading = True
        self._start_updating_loading_indicator()

    def set_completions(self, completions):
        self._is_loading = False
        self._stop_updating_loading_indicator()
        self._completions = completions
        self._render()

    def _render(self):
        if self._is_loading:
            self._control.text = '  {} Loading directories'.format(
                self._loading_indicator.current())
        else:
            if self._completions is None:
                self._control.text = ''
            else:
                self._control.text = '\n'.join(self._completions)

    def _start_updating_loading_indicator(self):
        self._stop_event.clear()
        def run():
            app = get_app()
            while not self._stop_event.is_set():
                self._loading_indicator.next()
                self._render()
                app.invalidate()
                time.sleep(0.5)
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def _stop_updating_loading_indicator(self):
        self._stop_event.set()


class RemoteDirectoryPromptScreen(object):

    def __init__(self, get_paths_in_directory):
        self._input = TextArea(text='/project/', multiline=False)
        self._completions_component = Completions()
        self.main_container = HSplit([
            Window(height=1),
            Window(
                FormattedTextControl(
                    'Choose directory to synchronize to on SherlockML: '
                ),
                height=1
            ),
            self._input,
            Window(height=1),
            self._completions_component.container
        ])
        self._get_paths_in_directory = get_paths_in_directory
        self._subdirectories_cache = {}
        self._buffer = self._input.buffer
        self._buffer.on_text_changed += self._handle_text_changed

    def on_mount(self, app):
        app.layout.focus(self.main_container)
        self._handle_text_changed()

    def _handle_text_changed(self, _=None):
        current_text = self._buffer.text
        directory = os.path.dirname(current_text)
        try:
            subdirectories = self._subdirectories_cache[directory]
        except KeyError:
            try:
                self._completions_component.set_loading()
                subdirectories = self._get_paths_in_directory(directory)
                self._subdirectories_cache[directory] = subdirectories
            except IOError:
                # remote basename does not exist
                subdirectories = []
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
        logging.info(matching_subdirectories)
        self._completions_component.set_completions(matching_subdirectories)

