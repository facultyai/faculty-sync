"""Prompt the user to update sml-sync"""

import errno
import json
import os
import time
from urllib.request import urlopen

import daiquiri
import semantic_version

from .version import version


TAGS_URL = 'https://api.bitbucket.org/2.0/repositories/theasi/sml-sync/refs/tags?pagelen=100'  # noqa

LOGGER = daiquiri.getLogger('version-check')


def _ensure_parent_exists(path):
    directory = os.path.dirname(path)
    try:
        os.makedirs(directory)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise


def _set_mtime(path):
    _ensure_parent_exists(path)
    if os.path.exists(path):
        os.utime(path)
    else:
        open(path, 'a').close()


def _last_update_path():
    xdg_cache_dir = os.environ.get('XDG_CACHE_DIR')

    if not xdg_cache_dir:
        xdg_cache_dir = os.path.expanduser('~/.cache')

    return os.path.join(xdg_cache_dir, 'sml-sync', 'last_update_check')


def _is_full_release(version):
    return not bool(version.prerelease)


def _get_versions():

    # Get to the last page of tags
    versions = []
    with urlopen(TAGS_URL, timeout=5) as response:
        json_response = json.load(response)
        versions.extend([
            semantic_version.Version(tag['name'])
            for tag in json_response['values']
        ])
    while 'next' in json_response:
        next_url = json_response['next']
        with urlopen(next_url, timeout=5) as response:
            json_response = json.load(response)
            versions.extend([
                semantic_version.Version(tag['name'])
                for tag in json_response['values']
            ])

    # Exclude release candidates and alpha releases
    full_versions = [
        version for version in versions
        if _is_full_release(version)
    ]
    return full_versions


def _check_for_new_release():
    current = semantic_version.Version(version)
    latest = max(_get_versions())
    LOGGER.info(
        'Latest version: {}, current version: {}, out-of-date: {}'.format(
            latest, current, current < latest))
    if current < latest:
        template = (
            "You are using sml-sync version {current}, however "
            "version {latest} is available.\n"
            "You should upgrade with:\n\n"
            "curl https://bitbucket.org/theasi/sml-sync/raw/{latest}/install.sh | bash"  # noqa
        )
        print(template.format(current=current, latest=latest))
    _set_mtime(_last_update_path())


def check_for_new_release():
    """Check for new releases, at most once every day."""
    check_pypi = True

    try:
        last_check_time = os.stat(_last_update_path()).st_mtime
        two_days_ago = time.time() - (2*86400)
        if last_check_time > two_days_ago:
            LOGGER.info(
                'Skipping update check as last update '
                'was {} seconds ago'.format(last_check_time)
            )
            check_pypi = False
    except OSError:
        pass

    if check_pypi:
        try:
            _check_for_new_release()
        except Exception:
            LOGGER.exception('Error checking for new release.')
