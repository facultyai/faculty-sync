
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import Window

from .diff import DifferencesScreen  # noqa
from .walking_trees import WalkingFileTreesScreen, WalkingFileTreesStatus  # noqa
from .watch_sync import WatchSyncScreen  # noqa
from .choose_remote_dir import RemoteDirectoryPromptScreen


class SynchronizationScreen(object):

    def __init__(self):
        self.main_container = Window(
            FormattedTextControl('Synchronizing'))
