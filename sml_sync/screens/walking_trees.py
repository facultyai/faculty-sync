
from enum import Enum
import time
import threading

from prompt_toolkit.layout import HSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.application.current import get_app

from .loading import LoadingIndicator


class WalkingFileTreesStatus(Enum):

    CONNECTING = 'CONNECTING'
    LOCAL_WALK = 'LOCAL_WALK'
    REMOTE_WALK = 'REMOTE_WALK'
    CALCULATING_DIFFERENCES = 'CALCULATING_DIFFERENCES'


class WalkingFileTreesScreen(object):

    def __init__(self, initial_status, exchange):
        self._status_control = FormattedTextControl('')
        self._loading_indicator = LoadingIndicator()
        self._status = None
        self.set_status(initial_status)
        self._bottom_toolbar = Window(
            FormattedTextControl('[q] Quit'),
            height=1, style='reverse')
        self.main_container = HSplit([
            Window(height=1),
            Window(self._status_control),
            self._bottom_toolbar
        ])
        self._exchange = exchange
        self._subscription_id = exchange.subscribe(
            Messages.WALK_STATUS_CHANGE,
            lambda new_status: self.set_status(new_status)
        )
        self._stop_event = threading.Event()
        self._thread = None
        self._start_updating_loading_indicator()

    def set_status(self, status):
        self._status = status
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

    def _render(self):
        loading_character = self._loading_indicator.current()
        if self._status == WalkingFileTreesStatus.CONNECTING:
            self._status_control.text = \
                '  {} Connecting to SherlockML server'.format(
                    loading_character)
        elif self._status == WalkingFileTreesStatus.LOCAL_WALK:
            self._status_control.text = \
                '  {} Walking local file tree'.format(loading_character)
        elif self._status == WalkingFileTreesStatus.REMOTE_WALK:
            self._status_control.text = \
                '  {} Walking file tree on SherlockML'.format(
                    loading_character)
        elif self._status == WalkingFileTreesStatus.CALCULATING_DIFFERENCES:
            self._status_control.text = (
                '  {} Calculating differences between '
                'local and remote file trees'.format(loading_character))

    def stop(self):
        self._stop_event.set()
        self._exchange.unsubscribe(self._subscription_id)
