import threading
import time
import traceback
import logging
from concurrent.futures import ThreadPoolExecutor

from .screens import (
    DifferencesScreen, WalkingFileTreesScreen,
    SynchronizationScreen, WatchSyncScreen,
    WalkingFileTreesStatus,
    RemoteDirectoryPromptScreen
)
from .file_trees import (
    compare_file_trees,
    remote_is_dir, get_remote_subdirectories
)
from .ssh import sftp_from_ssh_details
from .sync import Synchronizer
from .watch_sync import WatcherSynchronizer
from .pubsub import Messages


class Controller(object):

    def __init__(self, configuration, ssh_details, view, exchange):
        self._configuration = configuration
        self._ssh_details = ssh_details
        self._sftp = sftp_from_ssh_details(self._ssh_details)
        self._view = view
        self._exchange = exchange
        self._stop_event = threading.Event()
        self._current_screen = None
        self._current_screen_subscriptions = []
        self._thread = None
        self._executor = ThreadPoolExecutor(max_workers=8)
        self._synchronizer = None
        self._watcher_synchronizer = None

    def start(self):
        self._exchange.subscribe(
            Messages.STOP_CALLED,
            lambda _: self._stop_event.set()
        )
        self._exchange.subscribe(
            Messages.VERIFY_REMOTE_DIRECTORY,
            lambda directory:
                self._submit(
                    lambda: self._resolve_remote_directory(directory))
        )
        self._exchange.subscribe(
            Messages.PROMPT_FOR_REMOTE_DIRECTORY,
            lambda _: self._submit(self._prompt_for_remote_directory)
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

        self._exchange.publish(
            Messages.VERIFY_REMOTE_DIRECTORY,
            self._configuration.remote_dir
        )

    def _submit(self, fn, *args, **kwargs):
        future = self._executor.submit(fn, *args, **kwargs)
        try:
            future.result()
        except Exception:
            traceback.print_exc()

    def _resolve_remote_directory(self, remote_dir):
        if remote_dir is not None:
            if remote_is_dir(remote_dir, self._sftp):
                logging.info('Setting {} as remote directory'.format(
                    remote_dir))
                self._remote_dir = remote_dir
                self._synchronizer = Synchronizer(
                    self._configuration.local_dir,
                    self._remote_dir,
                    self._ssh_details,
                    self._configuration.ignore
                )
                self._exchange.publish(
                    Messages.REMOTE_DIRECTORY_SET,
                    self._remote_dir
                )
                self._exchange.publish(Messages.START_INITIAL_FILE_TREE_WALK)
            else:
                self._exchange.publish(Messages.PROMPT_FOR_REMOTE_DIRECTORY)
        else:
            self._exchange.publish(Messages.PROMPT_FOR_REMOTE_DIRECTORY)

    def _prompt_for_remote_directory(self):
        self._clear_current_subscriptions()
        self._current_screen = RemoteDirectoryPromptScreen(
            self._exchange,
            get_paths_in_directory=lambda directory: list(
                get_remote_subdirectories(directory, self._sftp))
        )
        self._view.mount(self._current_screen)

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
            self._exchange.publish(
                Messages.WALK_STATUS_CHANGE, WalkingFileTreesStatus.LOCAL_WALK)
            local_files = self._synchronizer.list_local()
            # local_files = walk_local_file_tree(
            #     self._configuration.local_dir,
            #     self._configuration.ignore
            # )
            logging.info(
                'Found {} files locally at path {}.'.format(
                    len(local_files), self._configuration.local_dir)
            )
            self._exchange.publish(
                Messages.WALK_STATUS_CHANGE,
                WalkingFileTreesStatus.REMOTE_WALK)
            # remote_files = walk_remote_file_tree(
            #     self._remote_dir, self._sftp, self._configuration.ignore)
            remote_files = self._synchronizer.list_remote()
            logging.info(
                'Found {} files on SherlockML at path {}.'.format(
                    len(remote_files), self._configuration.remote_dir)
            )
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
