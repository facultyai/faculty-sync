
import threading
import traceback

from prompt_toolkit.application import Application
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.key_binding.key_bindings import (
    KeyBindings, merge_key_bindings
)
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.layout.containers import Window

from .pubsub import Messages


class View(object):

    def __init__(self, configuration, exchange):
        self._project_name = configuration.project.name
        self._local_dir = configuration.local_dir
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
        if screen.bindings is not None:
            if screen.use_default_bindings:
                merged_key_bindings = merge_key_bindings([
                    self.bindings, screen.bindings
                ])
                self.application.key_bindings = merged_key_bindings
            else:
                self.application.key_bindings = screen.bindings
        else:
            # Screen does not define additional keybindings
            self.application.key_bindings = self.bindings
        screen.on_mount(self.application)

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
            'SherlockML synchronizer  '
            '{local_dir} -> '
            '{project_name}'
        ).format(
            local_dir=self._local_dir,
            project_name=self._project_name
        )
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
            self.exchange.publish(Messages.STOP_CALLED)

        return bindings
