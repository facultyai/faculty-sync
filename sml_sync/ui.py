
import logging
import threading
import traceback
import signal

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.eventloop import get_event_loop

from .pubsub import Messages


class View(object):

    def __init__(self, configuration, exchange):
        self._project_name = configuration.project.name
        self._local_dir = configuration.local_dir
        self._remote_directory = None
        self._exchange = exchange
        self._loop = get_event_loop()

        self._current_screen = None
        self.root_container = HSplit([Window()])
        self.layout = Layout(container=self.root_container)
        self._render()

        self.bindings = self._create_bindings()

        self.application = Application(
            layout=self.layout,
            key_bindings=self.bindings,
            full_screen=True
        )

        self._exchange.subscribe(
            Messages.REMOTE_DIRECTORY_SET,
            self._set_remote_dir
        )

    def _render(self):
        top_toolbar = self._render_top_toolbar()
        if self._current_screen is not None:
            main_container = self._current_screen.main_container
        else:
            main_container = Window()
        self.root_container.children = [top_toolbar, main_container]

    def mount(self, screen):
        """
        Mount a screen into the view.

        The screen must have a `main_container` attribute and,
        optionally, a `bindings` attribute.
        """
        if self._current_screen is not None:
            self._current_screen.stop()
        self._current_screen = screen
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
        self._render()
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
        self._register_resize_handler()

    def stop(self):
        if self.application.is_running:
            self.application.exit()
            self._remove_resize_handler()

    def _register_resize_handler(self):
        # The application receives the signal SIGWINCH
        # when the terminal has been resized.
        self._has_sigwinch = hasattr(signal, 'SIGWINCH')
        if self._has_sigwinch:
            self._previous_winch_handler = self._loop.add_signal_handler(
                signal.SIGWINCH, self._on_resize)

    def _remove_resize_handler(self):
        # Remove WINCH handler.
        if self._has_sigwinch:
            self._loop.add_signal_handler(
                signal.SIGWINCH, self._previous_winch_handler)

    def _on_resize(self):
        logging.info('Handling application resize event.')
        self.application.invalidate()

    def _render_top_toolbar(self):
        remote_directory_text = (
            ':{}'.format(self._remote_directory)
            if self._remote_directory is not None
            else ''
        )
        top_text = (
            '[SherlockML synchronizer]  '
            '{local_dir} -> '
            '{project_name}{remote_directory_text}'
        ).format(
            local_dir=self._local_dir,
            project_name=self._project_name,
            remote_directory_text=remote_directory_text
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
            self._exchange.publish(Messages.STOP_CALLED)

        return bindings

    def _set_remote_dir(self, directory):
        self._remote_directory = directory
        self._render()
