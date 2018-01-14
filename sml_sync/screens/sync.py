
from prompt_toolkit.layout import HSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import Window

from .base import BaseScreen


class SynchronizationScreen(BaseScreen):

    def __init__(self):
        super().__init__()
        self.main_container = HSplit([
            Window(height=1),
            Window(FormattedTextControl('  Synchronizing'), height=1)
        ])
