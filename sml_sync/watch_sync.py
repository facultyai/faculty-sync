
import threading
import os
import queue
from datetime import datetime

import watchdog.observers
import watchdog.events

from .file_trees import (
    walk_local_file_tree, walk_remote_file_tree, get_remote_mtime,
    compare_file_trees
)
from .models import FsObjectType, ChangeEventType, FsChangeEvent
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
        del self._data[path]

    def _was_modified_since(self, path, timestamp):
        current_timestamp = self._data.get(path, datetime.min)
        return current_timestamp > timestamp

    def update_if_newer(self, path, timestamp):
        if not self._was_modified_since(path, timestamp):
            self._data[path] = timestamp

    @classmethod
    def from_fs_objects(cls, fs_objects, path_prefix):
        _data = {}
        for fs_object in fs_objects:
            if fs_object.obj_type == FsObjectType.FILE:
                last_modified, _ = fs_object.attrs
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

    def __init__(self, queue, local_dir):
        self.queue = queue
        self.local_dir = local_dir

    def on_any_event(self, event):
        event_type = self.watchdog_event_lookup[event.event_type]
        is_directory = event.is_directory
        path = os.path.relpath(
            event.src_path,
            start=self.local_dir
        )
        self.queue.put(FsChangeEvent(event_type, is_directory, path))


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
                    self._handle_sync(fs_event)
                    self._monitor.has_synced(fs_event)
                else:
                    pass
        self._thread = threading.Thread(target=run)
        self._thread.start()

    def _handle_sync(self, fs_event):
        if fs_event.is_directory:
            # TODO implement directory handling
            pass
        else:
            path = fs_event.path
            self._exchange.publish(
                Messages.STARTING_HANDLING_FS_EVENT,
                fs_event
            )
            if fs_event.event_type in \
               {ChangeEventType.CREATED, ChangeEventType.MODIFIED}:
                self._synchronizer.up(path)
            elif fs_event.event_type == ChangeEventType.DELETED:
                self._synchronizer.rmfile_remote(path)
            self._exchange.publish(
                Messages.FINISHED_HANDLING_FS_EVENT,
                fs_event
            )

    def join(self):
        if self._thread is not None:
            self._thread.join()


class HeldFilesMonitor(object):

    def __init__(self, local_dir, remote_dir, sftp, exchange):
        self._local_dir = local_dir
        self._remote_dir = remote_dir
        self._sftp = sftp
        self._exchange = exchange
        _local_tree = walk_local_file_tree(self._local_dir)
        _remote_tree = walk_remote_file_tree(self._remote_dir, sftp)
        self._local_timestamps = TimestampDatabase.from_fs_objects(
            _local_tree, local_dir)
        self._remote_timestamps = TimestampDatabase.from_fs_objects(
            _remote_tree, remote_dir)
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
                local_mtime, _ = difference[1].attrs
                remote_mtime, _ = difference[2].attrs
                if remote_mtime > local_mtime:
                    # Hold only if remote file was modified after current
                    yield difference[1].path

    def should_sync(self, fs_event):
        path = fs_event.path
        if path in self._held_paths:
            return False
        else:
            last_known_timestamp = self._remote_timestamps.get(path)
            try:
                current_timestamp = get_remote_mtime(
                    os.path.join(self._remote_dir, path), self._sftp)
                has_changed = last_known_timestamp != current_timestamp
                if has_changed:
                    self._held_paths.add(path)
                    self._exchange.publish(
                        Messages.HELD_FILES_CHANGED,
                        frozenset(self._held_paths)
                    )
                    return False
                else:
                    return True
            except FileNotFoundError:
                return True

    def has_synced(self, fs_event):
        if fs_event.event_type == ChangeEventType.DELETED:
            self._remote_timestamps.remove(fs_event.path)
        else:
            path = fs_event.path
            current_timestamp = get_remote_mtime(
                os.path.join(self._remote_dir, path), self._sftp)
            self._remote_timestamps.update_if_newer(path, current_timestamp)


class WatcherSynchronizer(object):

    def __init__(self, local_dir, remote_dir, sftp, synchronizer, exchange):
        self.queue = ListableQueue()
        self.observer = watchdog.observers.Observer()
        self._exchange = exchange
        monitor = HeldFilesMonitor(local_dir, remote_dir, sftp, exchange)
        self.observer.schedule(
            FileSystemChangeHandler(self.queue, local_dir),
            local_dir,
            recursive=True
        )
        self.uploader = Uploader(self.queue, synchronizer, monitor, exchange)

    def start(self):
        self._exchange.publish('START_WATCH_SYNC_MAIN_LOOP')
        self.observer.start()
        self.uploader.start()

    def stop(self):
        self.observer.stop()
        self.uploader.stop()

    def join(self):
        self.observer.join()
        self.uploader.join()
