
import threading
from queue import Queue, Empty
import uuid
from enum import Enum


class Messages(Enum):
    HELD_FILES_CHANGED = 'HELD_FILES_CHANGED'
    STARTING_FILE_SYNC = 'STARTING_FILE_SYNC'
    FINISHED_FILE_SYNC = 'FINISHED_FILE_SYNC'

    STARTING_HANDLING_FS_EVENT = 'STARTING_HANDLING_FS_EVENT'
    FINISHED_HANDLING_FS_EVENT = 'FINISHED_HANDLING_FS_EVENT'
    ERROR_HANDLING_FS_EVENT = 'ERROR_HANDLING_FS_EVENT'

    STOP_WATCH_SYNC = 'STOP_WATCH_SYNC'


class PubSubExchange(object):

    def __init__(self):
        self.queue = Queue()
        self.subscribers = {}
        self._dispatcher = None
        self._stop_event = threading.Event()

    def publish(self, message_type, message_data=None):
        self.queue.put((message_type, message_data))

    def subscribe(self, msg_type, callback):
        subscription_id = uuid.uuid4()
        try:
            subscribers = self.subscribers[msg_type]
            subscribers.append((subscription_id, callback))
        except KeyError:
            self.subscribers[msg_type] = [(subscription_id, callback)]
        return subscription_id

    def start(self):
        if self._dispatcher is not None:
            raise ValueError('Exchange is already running')

        def run():
            while not self._stop_event.is_set():
                try:
                    message_type, message_data = self.queue.get(timeout=1)
                    try:
                        subscribers = self.subscribers[message_type]
                        for (subscription_id, callback) in subscribers:
                            callback(message_data)
                    except KeyError:
                        pass
                except Empty:
                    pass

        self._dispatcher = threading.Thread(target=run)
        self._dispatcher.start()

    def join(self):
        if self._dispatcher is not None:
            self._dispatcher.join()

    def stop(self):
        self._stop_event.set()

    def unsubscribe(self, subscription_id):
        # TODO: Inefficient and probably full of race conditions
        for msg_type, subscribers in self.subscribers.items():
            self.subscribers[msg_type] = [
                subscriber for subscriber in subscribers if
                subscriber[0] != subscription_id
            ]
