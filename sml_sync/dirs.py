import os
import errno


def ensure_parent_exists(path):
    directory = os.path.dirname(path)
    try:
        os.makedirs(directory)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
