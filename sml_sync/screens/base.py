
from prompt_toolkit.key_binding.key_bindings import KeyBindings


class BaseScreen(object):

    def __init__(self):
        self.main_container = None
        self.bindings = KeyBindings()
        self.use_default_bindings = True

    def on_mount(self, application):
        pass

    def stop(self):
        pass
