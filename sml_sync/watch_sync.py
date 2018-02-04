
import logging
import os
import queue
import threading
from datetime import datetime

import watchdog.events
import watchdog.observers

from . import path_match
from .file_trees import compare_file_trees, get_remote_mtime
from .models import ChangeEventType, FsChangeEvent
from .pubsub import Messages


class TimestampDatabase(object):

    def __init__(self, initial_data=None):
        """
        Keep track of paths and timestamps associated with those paths.

        Not thread-safe
        """
        if initial_data is None:
            self._data = {}
        else:
            self._data = initial_data

    def __str__(self):
        return str(self._data)

    def get(self, path, default=datetime.min):
        return self._data.get(path, default)

    def remove(self, path):
        try:
            del self._data[path]
        except KeyError:
            logging.info(
                'Path {} did not exist in timestamp database'.format(path)
            )

    def _was_modified_since(self, path, timestamp):
        current_timestamp = self._data.get(path, datetime.min)
        return current_timestamp > timestamp

    def update_if_newer(self, path, timestamp):
        if not self._was_modified_since(path, timestamp):
            self._data[path] = timestamp

    @classmethod
    def from_fs_objects(cls, fs_objects):
        _data = {}
        for fs_object in fs_objects:
            last_modified = fs_object.attrs.last_modified
            _data[fs_object.path] = last_modified
        return cls(_data)


class ListableQueue(queue.Queue):

    def items(self):
        return [item for item in self.queue]


class FileSystemChangeHandler(watchdog.events.FileSystemEventHandler):

    watchdog_event_lookup = {
        watchdog.events.EVENT_TYPE_CREATED: ChangeEventType.CREATED,
        watchdog.events.EVENT_TYPE_MOVED: ChangeEventType.MOVED,
        watchdog.events.EVENT_TYPE_MODIFIED: ChangeEventType.MODIFIED,
        watchdog.events.EVENT_TYPE_DELETED: ChangeEventType.DELETED
    }

    def __init__(self, queue, local_dir, excluded_patterns):
        self.queue = queue
        self.local_dir = local_dir
        self._excluded_patterns = excluded_patterns

    def on_any_event(self, watchdog_event):
        logging.info('Registered filesystem event {}'.format(watchdog_event))
        event_type = self.watchdog_event_lookup[watchdog_event.event_type]
        is_directory = watchdog_event.is_directory
        path = self._relpath(watchdog_event.src_path)
        if path_match.matches_any_of(path, self._excluded_patterns):
            logging.info(
                'Ignoring change event {} as it is in list of excluded patterns.'.format(
                    watchdog_event)
            )
        elif event_type == ChangeEventType.MODIFIED and is_directory:
            # Ignore directory mtime changes
            pass
        else:
            if event_type == ChangeEventType.MOVED:
                dest_path = watchdog_event.dest_path
                abs_local_dir = os.path.abspath(self.local_dir)
                if os.path.abspath(dest_path).startswith(abs_local_dir):
                    event = FsChangeEvent(
                        event_type,
                        is_directory,
                        path,
                        extra_args={'dest_path': self._relpath(dest_path)}
                    )
                else:
                    # File was moved outside of the area we're watching:
                    # treat as deletion
                    event = FsChangeEvent(
                        ChangeEventType.DELETED,
                        is_directory,
                        path,
                        extra_args=None
                    )
            else:
                event = FsChangeEvent(
                    event_type, is_directory, path, extra_args=None)
            self.queue.put(event)

    def _relpath(self, path):
        return os.path.relpath(path, start=self.local_dir)


class Uploader(object):

    def __init__(self, queue, synchronizer, monitor, exchange):
        self._queue = queue
        self._synchronizer = synchronizer
        self._stop_event = threading.Event()
        self._monitor = monitor
        self._thread = None
        self._exchange = exchange

    def stop(self):
        self._stop_event.set()

    def start(self):
        def run():
            while not self._stop_event.is_set():
                try:
                    fs_event = self._queue.get(timeout=1)
                except queue.Empty:
                    continue
                if self._monitor.should_sync(fs_event):
                    try:
                        self._handle_sync(fs_event)
                        self._monitor.has_synced(fs_event)
                    except Exception as exc:
                        logging.exception(exc)
                        self._exchange.publish(
                            Messages.ERROR_HANDLING_FS_EVENT
                        )

        self._thread = threading.Thread(target=run)
        self._thread.start()

    def _handle_sync(self, fs_event):
        logging.info('Processing file system event {}'.format(fs_event))
        self._exchange.publish(
            Messages.STARTING_HANDLING_FS_EVENT,
            fs_event
        )
        if fs_event.is_directory:
            # TODO implement directory handling
            if fs_event.event_type in \
             {ChangeEventType.CREATED, ChangeEventType.MODIFIED}:
                self._synchronizer.mkdir_remote(fs_event.path)
            elif fs_event.event_type == ChangeEventType.DELETED:
                self._synchronizer.rmdir_remote(fs_event.path)
            elif fs_event.event_type == ChangeEventType.MOVED:
                self._synchronizer.mvfile_remote(
                    fs_event.path,
                    fs_event.extra_args['dest_path']
                )
        else:
            path = fs_event.path
            if fs_event.event_type in \
             {ChangeEventType.CREATED, ChangeEventType.MODIFIED}:
                self._synchronizer.up(path)
            elif fs_event.event_type == ChangeEventType.DELETED:
                self._synchronizer.rmfile_remote(path)
            elif fs_event.event_type == ChangeEventType.MOVED:
                self._synchronizer.mvfile_remote(
                    path,
                    fs_event.extra_args['dest_path']
                )
        self._exchange.publish(
            Messages.FINISHED_HANDLING_FS_EVENT,
            fs_event
        )

    def join(self):
        if self._thread is not None:
            self._thread.join()


class HeldFilesMonitor(object):

    def __init__(self, synchronizer, sftp, exchange):
        self._synchronizer = synchronizer
        self._local_dir = synchronizer.local_dir
        self._remote_dir = synchronizer.remote_dir
        self._sftp = sftp
        self._exchange = exchange
        _local_tree = self._synchronizer.list_local()
        _remote_tree = self._synchronizer.list_remote()
        self._local_timestamps = TimestampDatabase.from_fs_objects(
            _local_tree)
        self._remote_timestamps = TimestampDatabase.from_fs_objects(
            _remote_tree)
        self._held_paths = set(
            self._get_initial_help_paths(_local_tree, _remote_tree))
        self._exchange.publish(
            Messages.HELD_FILES_CHANGED,
            frozenset(self._held_paths)
        )

    def _get_initial_help_paths(self, local_tree, remote_tree):
        for difference in compare_file_trees(local_tree, remote_tree):
            if difference[0] in {'RIGHT_ONLY', 'TYPE_DIFFERENT'}:
                yield difference[1].path
            elif difference[0] == 'ATTRS_DIFFERENT':
                local_mtime = difference[1].attrs.last_modified
                remote_mtime = difference[2].attrs.last_modified
                if remote_mtime > local_mtime:
                    # Hold only if remote file was modified after current
                    yield difference[1].path

    def should_sync(self, fs_event):
        path = fs_event.path
        if path in self._held_paths:
            return False
        else:
            if fs_event.event_type == ChangeEventType.MOVED:
                dest_path = fs_event.extra_args['dest_path']
                if self._has_path_changed(path):
                    self._add_to_held_paths(path)
                    src_path_unchanged = False
                else:
                    src_path_unchanged = True
                if self._has_path_changed(dest_path):
                    self._add_to_held_paths(dest_path)
                    dest_path_unchanged = False
                else:
                    dest_path_unchanged = True
                return src_path_unchanged and dest_path_unchanged
            else:
                if self._has_path_changed(path):
                    self._add_to_held_paths(path)
                    return False
                else:
                    return True

    def _has_path_changed(self, path):
        last_known_timestamp = self._remote_timestamps.get(path)
        try:
            current_timestamp = get_remote_mtime(
                os.path.join(self._remote_dir, path), self._sftp)
            has_changed = last_known_timestamp != current_timestamp
            return has_changed
        except FileNotFoundError:
            return False

    def _add_to_held_paths(self, path):
        self._held_paths.add(path)
        self._exchange.publish(
            Messages.HELD_FILES_CHANGED,
            frozenset(self._held_paths)
        )

    def has_synced(self, fs_event):
        if fs_event.event_type == ChangeEventType.DELETED:
            self._remote_timestamps.remove(fs_event.path)
        elif fs_event.event_type == ChangeEventType.MOVED:
            self._remote_timestamps.remove(fs_event.path)
            dest_path = fs_event.extra_args['dest_path']
            abs_dest_path = os.path.join(self._remote_dir, dest_path)
            current_timestamp = get_remote_mtime(abs_dest_path, self._sftp)
            self._remote_timestamps.update_if_newer(
                dest_path, current_timestamp)
        else:
            path = fs_event.path
            current_timestamp = get_remote_mtime(
                os.path.join(self._remote_dir, path), self._sftp)
            self._remote_timestamps.update_if_newer(path, current_timestamp)


class WatcherSynchronizer(object):

    def __init__(self, sftp, synchronizer, exchange):
        local_dir = synchronizer.local_dir
        self.queue = ListableQueue()
        self.observer = watchdog.observers.Observer()
        self._exchange = exchange
        monitor = HeldFilesMonitor(synchronizer, sftp, exchange)
        self.observer.schedule(
            FileSystemChangeHandler(
                self.queue,
                local_dir,
                synchronizer.ignore_paths
            ),
            local_dir,
            recursive=True
        )
        self.uploader = Uploader(self.queue, synchronizer, monitor, exchange)

    def start(self):
        self._exchange.publish(Messages.START_WATCH_SYNC_MAIN_LOOP)
        self.observer.start()
        self.uploader.start()

    def stop(self):
        self.observer.stop()
        self.uploader.stop()

    def join(self):
        self.observer.join()
        self.uploader.join()
