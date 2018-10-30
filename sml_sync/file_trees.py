import os
import stat
from datetime import datetime

from .models import FsObjectType, Difference, DifferenceType


def get_remote_mtime(path, sftp):
    return _get_mtime(path, sftp)


def remote_is_dir(path, sftp):
    try:
        path_stat = sftp.stat(path)
        return stat.S_ISDIR(path_stat.st_mode)
    except FileNotFoundError:
        return False


def get_remote_subdirectories(path, sftp):
    """ Get directories below path """
    for obj_name in sftp.listdir(path):
        full_path = os.path.join(path, obj_name)
        is_directory = stat.S_ISDIR(sftp.stat(full_path).st_mode)
        if is_directory:
            yield full_path


def _get_mtime(path, oslike):
    return datetime.fromtimestamp(int(oslike.stat(path).st_mtime))


def compare_file_trees(left, right):
    left_file_paths = {obj.path: obj for obj in left}
    right_file_paths = {obj.path: obj for obj in right}
    left_only = [obj for obj in left if obj.path not in right_file_paths]
    for obj in left_only:
        yield Difference(DifferenceType.LEFT_ONLY, left=obj, right=None)
    right_only = [obj for obj in right if obj.path not in left_file_paths]
    for obj in right_only:
        yield Difference(DifferenceType.RIGHT_ONLY, left=None, right=obj)

    for left_obj in left:
        if left_obj.path in right_file_paths:
            right_obj = right_file_paths[left_obj.path]
            if left_obj.obj_type != right_obj.obj_type:
                yield Difference(
                    DifferenceType.TYPE_DIFFERENT, left_obj, right_obj
                )
            elif (
                left_obj.attrs != right_obj.attrs
                and left_obj.obj_type == FsObjectType.FILE
            ):
                yield Difference(
                    DifferenceType.ATTRS_DIFFERENT, left_obj, right_obj
                )
