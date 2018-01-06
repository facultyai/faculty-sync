
import time
import threading
import traceback
import logging
from concurrent.futures import ThreadPoolExecutor

import daiquiri

from .cli import parse_command_line
from .ssh import get_ssh_details, sftp_from_ssh_details
from .pubsub import PubSubExchange, Messages
from .ui import View
from .screens import (
    DifferencesScreen, WalkingFileTreesScreen,
    SynchronizationScreen, WatchSyncScreen,
    WalkingFileTreesStatus
)
from .file_trees import (
    walk_local_file_tree, walk_remote_file_tree, compare_file_trees)
from .sync import Synchronizer
from .watch_sync import WatcherSynchronizer


daiquiri.setup(
    level=logging.INFO,
    outputs=[daiquiri.output.File('sml-sync.log')]
)


class Controller(object):

    def __init__(self, configuration, ssh_details, view, exchange):
        self._configuration = configuration
        self._ssh_details = ssh_details
        self._sftp = None
        self._view = view
        self._exchange = exchange
        self._stop_event = threading.Event()
        self._current_screen = None
        self._current_screen_subscriptions = []
        self._thread = None
        self._executor = ThreadPoolExecutor(max_workers=8)
        self._synchronizer = Synchronizer(
            configuration.local_dir,
            configuration.remote_dir,
            ssh_details
        )
        self._watcher_synchronizer = None

    def start(self):
        self._exchange.subscribe(
            Messages.STOP_CALLED,
            lambda _: self._stop_event.set()
        )
        self._exchange.subscribe(
            Messages.START_INITIAL_FILE_TREE_WALK,
            lambda _: self._submit(self._get_differences)
        )
        self._exchange.subscribe(
            Messages.DISPLAY_DIFFERENCES,
            lambda differences: self._submit(
                self._display_differences, differences)
        )
        self._exchange.subscribe(
            Messages.SYNC_SHERLOCKML_TO_LOCAL,
            lambda _: self._submit(self._sync_sherlockml_to_local)
        )
        self._exchange.subscribe(
            Messages.SYNC_LOCAL_TO_SHERLOCKML,
            lambda _: self._submit(self._sync_local_to_sherlockml)
        )
        self._exchange.subscribe(
            Messages.START_WATCH_SYNC,
            lambda _: self._submit(self._start_watch_sync)
        )
        self._exchange.subscribe(
            Messages.ERROR_HANDLING_FS_EVENT,
            lambda _: self._submit(self._restart_watch_sync)
        )
        self._exchange.subscribe(
            Messages.STOP_WATCH_SYNC,
            lambda _: self._submit(self._stop_watch_sync)
        )

        def run():
            while not self._stop_event.is_set():
                time.sleep(0.1)

        self._thread = threading.Thread(target=run)
        self._thread.start()

        self._exchange.publish(Messages.START_INITIAL_FILE_TREE_WALK)

    def _submit(self, fn, *args, **kwargs):
        future = self._executor.submit(fn, *args, **kwargs)
        try:
            future.result()
        except Exception as e:
            traceback.print_exc()

    def _sync_sherlockml_to_local(self):
        self._clear_current_subscriptions()
        self._current_screen = SynchronizationScreen()
        self._synchronizer.down(rsync_opts=['--delete'])
        self._view.mount(self._current_screen)
        self._get_differences()

    def _sync_local_to_sherlockml(self):
        self._clear_current_subscriptions()
        self._current_screen = SynchronizationScreen()
        self._synchronizer.up(rsync_opts=['--delete'])
        self._view.mount(self._current_screen)
        self._get_differences()

    def _display_differences(self, differences):
        self._clear_current_subscriptions()
        self._current_screen = DifferencesScreen(differences, self._exchange)
        subscription_id = self._exchange.subscribe(
            Messages.REFRESH_DIFFERENCES,
            lambda _: self._submit(self._get_differences)
        )
        self._current_screen_subscriptions.append(subscription_id)
        self._view.mount(self._current_screen)

    def _clear_current_subscriptions(self):
        for subscription_id in self._current_screen_subscriptions:
            self._exchange.unsubscribe(subscription_id)

    def _get_differences(self):
        self._clear_current_subscriptions()
        self._current_screen = WalkingFileTreesScreen(
            WalkingFileTreesStatus.CONNECTING, self._exchange)
        try:
            self._view.mount(self._current_screen)
            self._sftp = sftp_from_ssh_details(self._ssh_details)
            self._exchange.publish(
                Messages.WALK_STATUS_CHANGE, WalkingFileTreesStatus.LOCAL_WALK)
            local_files = walk_local_file_tree(self._configuration.local_dir)
            self._exchange.publish(
                Messages.WALK_STATUS_CHANGE, WalkingFileTreesStatus.REMOTE_WALK)
            remote_files = walk_remote_file_tree(
                self._configuration.remote_dir, self._sftp)
            self._exchange.publish(
                Messages.WALK_STATUS_CHANGE,
                WalkingFileTreesStatus.CALCULATING_DIFFERENCES)
            differences = list(compare_file_trees(local_files, remote_files))
            self._exchange.publish(Messages.DISPLAY_DIFFERENCES, differences)
        finally:
            self._current_screen.stop()

    def _start_watch_sync(self):
        self._clear_current_subscriptions()
        self._current_screen = WatchSyncScreen(self._exchange)
        self._view.mount(self._current_screen)
        self._watcher_synchronizer = WatcherSynchronizer(
            self._configuration.local_dir,
            self._configuration.remote_dir,
            self._sftp,
            self._synchronizer,
            self._exchange
        )
        self._watcher_synchronizer.start()

    def _restart_watch_sync(self):
        self._clear_current_subscriptions()
        if self._watcher_synchronizer is not None:
            self._watcher_synchronizer.stop()
        self._synchronizer.up(rsync_opts=['--delete'])
        self._start_watch_sync()

    def _stop_watch_sync(self):
        logging.info('Stopping watch-synchronization loop.')
        if self._watcher_synchronizer is not None:
            self._watcher_synchronizer.stop()
        self._get_differences()

    def join(self):
        self._thread.join()


def main():
    try:
        configuration = parse_command_line()
    except Exception as e:
        print(e)
        exit(1)

    exchange = PubSubExchange()
    exchange.start()
    view = View(configuration, exchange)
    view.start()

    with get_ssh_details(configuration) as ssh_details:
        controller = Controller(configuration, ssh_details, view, exchange)
        controller.start()

        # Run until the controller stops
        controller.join()

    view.stop()
    exchange.stop()
    exchange.join()


main()
