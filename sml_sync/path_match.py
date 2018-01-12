import os
from fnmatch import fnmatch


def matches(path, pattern):
    """
    Matches rsync-like pattern

    Currently should obey the same rules as rsync, apart from ** patterns
    """
    path = os.path.normpath(path)
    if pattern == '/':
        return True
    else:
        pattern = pattern.rstrip('/')
        if pattern.startswith('/'):
            return _anchored_match(path, pattern.lstrip('/'))
        else:
            return _floating_match(path, pattern)


def _anchored_match(path, pattern):
    path_components = _get_path_components(path)
    pattern_components = _get_path_components(pattern)
    return _anchored_match_helper(path_components, pattern_components)


def _floating_match(path, pattern):
    path_components = _get_path_components(path)
    pattern_components = _get_path_components(pattern)
    for i in range(len(path_components)):
        subpath_components = path_components[i:]
        if _anchored_match_helper(subpath_components, pattern_components):
            return True
    return False


def _anchored_match_helper(path_components, pattern_components):
    if len(pattern_components) > len(path_components):
        return False
    elif len(pattern_components) == 0:
        return True
    elif len(pattern_components) == 1:
        return fnmatch(path_components[0], pattern_components[0])
    else:
        return (
            fnmatch(path_components[0], pattern_components[0]) and
            _anchored_match_helper(path_components[1:], pattern_components[1:])
        )


def _get_path_components(path):
    path_components = []
    while path and path != '/':
        path, tail = os.path.split(path)
        path_components.append(tail)
    path_components.reverse()
    return path_components
