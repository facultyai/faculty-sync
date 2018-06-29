
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

    def is_file(self):
        return self.obj_type == FsObjectType.FILE

    def is_directory(self):
        return self.obj_type == FsObjectType.DIRECTORY


FileAttrs = collections.namedtuple('FileAttrs', ['last_modified', 'size'])
DirectoryAttrs = collections.namedtuple('DirectoryAttrs', ['last_modified'])


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
    ['event_type', 'is_directory', 'path', 'extra_args']
)


class DifferenceType(Enum):
    # path exists only in left tree
    LEFT_ONLY = 'LEFT_ONLY'

    # path exists only in right tree
    RIGHT_ONLY = 'RIGHT_ONLY'

    # path exists in both, but is a file in one and a directory in the other
    TYPE_DIFFERENT = 'TYPE_DIFFERENT'

    # path exists in both, but they have different attributes
    ATTRS_DIFFERENT = 'ATTRS_DIFFERENT'


Difference = collections.namedtuple(
    'Difference', ['difference_type', 'left', 'right'])
