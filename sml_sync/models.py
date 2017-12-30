
import collections
import os
from enum import Enum


class FsObjectType(Enum):
    FILE = 'FILE'
    DIRECTORY = 'DIRECTORY'


class FsObject(
        collections.namedtuple('FsObject', ['path', 'obj_type', 'attrs'])):

    def without_path_prefix(self, prefix):
        return FsObject(
            os.path.relpath(self.path, prefix),
            self.obj_type,
            self.attrs
        )


Configuration = collections.namedtuple(
    'Configuration',
    ['project_id', 'server_id', 'local_dir', 'remote_dir']
)

SshDetails = collections.namedtuple(
    'SshDetails',
    ['hostname', 'port', 'username', 'key_file']
)


class ChangeEventType(Enum):
    CREATED = 'CREATED'
    MOVED = 'MOVED'
    MODIFIED = 'MODIFIED'
    DELETED = 'DELETED'


FsChangeEvent = collections.namedtuple(
    'FsChangeEvent',
    ['event_type', 'is_directory', 'path']
)
