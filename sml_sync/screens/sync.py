import threading
import time
from enum import Enum

from prompt_toolkit.application.current import get_app
from prompt_toolkit.layout import HSplit
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl

from .base import BaseScreen
from .loading import LoadingIndicator


class SynchronizationScreenDirection(Enum):
    UP = 'up'
    DOWN = 'down'


class SynchronizationScreen(BaseScreen):
    def __init__(self, direction):
        super().__init__()
        self._direction = direction
        self._loading_indicator = LoadingIndicator()
        self._stop_event = threading.Event()
        self._control = FormattedTextControl('')
        self.main_container = HSplit(
            [Window(height=1), Window(self._control, height=1)]
        )
        self._start_updating_loading_indicator()

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

    def _render(self):
        direction_text = (
            'from local filesystem to SherlockML'
            if self._direction == SynchronizationScreenDirection.UP
            else 'from SherlockML to local filesystem'
        )
        self._control.text = '  {} Synchronizing {}'.format(
            self._loading_indicator.current(), direction_text
        )

    def stop(self):
        self._stop_event.set()
