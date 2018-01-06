
import os
import stat
from datetime import datetime

from .models import FsObject, FsObjectType, FileAttrs, DirectoryAttrs


def get_remote_mtime(path, sftp):
    return _get_mtime(path, sftp)


def remote_is_dir(path, sftp):
    try:
        path_stat = sftp.stat(path)
        return stat.S_ISDIR(path_stat).st_mode
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


def walk_local_file_tree(base):
    return list(_walk_file_tree(base, os))


def walk_remote_file_tree(base, sftp):
    return list(_walk_file_tree(base, sftp))


def compare_file_trees(left, right):
    left_file_paths = {obj.path: obj for obj in left}
    right_file_paths = {obj.path: obj for obj in right}
    left_only = [obj for obj in left if obj.path not in right_file_paths]
    for obj in left_only:
        yield ('LEFT_ONLY', obj)
    right_only = [obj for obj in right if obj.path not in left_file_paths]
    for obj in right_only:
        yield ('RIGHT_ONLY', obj)

    for left_obj in left:
        if left_obj.path in right_file_paths:
            right_obj = right_file_paths[left_obj.path]
            if left_obj.obj_type != right_obj.obj_type:
                yield ('TYPE_DIFFERENT', left_obj, right_obj)
            elif left_obj.attrs != right_obj.attrs:
                yield ('ATTRS_DIFFERENT', left_obj, right_obj)


def _walk_file_tree(base, oslike):
    files_with_absolute_paths = _walk_file_tree_helper(base, oslike)
    return (f.without_path_prefix(base) for f in files_with_absolute_paths)


def _walk_file_tree_helper(base, oslike):
    """ Call recursively to walk a file tree """
    for obj_name in oslike.listdir(base):
        path = os.path.join(base, obj_name)
        is_directory = stat.S_ISDIR(oslike.stat(path).st_mode)
        if is_directory:
            mtime = _get_mtime(path, oslike)
            yield FsObject(path, FsObjectType.DIRECTORY, DirectoryAttrs(mtime))
            for fs_object in _walk_file_tree_helper(path, oslike):
                yield fs_object
        else:
            size = oslike.stat(path).st_size
            mtime = _get_mtime(path, oslike)
            yield FsObject(path, FsObjectType.FILE, FileAttrs(mtime, size))
