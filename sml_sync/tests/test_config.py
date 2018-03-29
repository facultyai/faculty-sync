import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from ..config import get_config, FileConfiguration


# Note that, for compatibility with Python3.5, the local directory
# has to exist. In most of these tests, we just pass os.getcwd()
# as the local directory.

LOCAL_DIRECTORY = os.getcwd()

# Another version of the local directory, but
# with `/path/to/home` replaced by a tilde.
LOCAL_DIRECTORY_WITH_TILDE = LOCAL_DIRECTORY.replace(
    os.path.expanduser('~'), '~', 1
)


@contextmanager
def _temporary_configurations(user_config=None, project_config=None):
    with tempfile.TemporaryDirectory() as temporary_directory:
        path = Path(temporary_directory)
        user_configuration_path = path / 'user.conf'
        project_configuration_path = path / 'project.conf'
        if user_config is not None:
            with user_configuration_path.open('w') as fp:
                fp.write(user_config)
        if project_config is not None:
            with project_configuration_path.open('w') as fp:
                fp.write(project_config)
        yield (project_configuration_path, user_configuration_path)


@pytest.mark.parametrize(
    'config,expected',
    [
        (
            """
            [default]
            project = acme
            remote = /project/dir22
            """,
            FileConfiguration('acme', '/project/dir22', None, [])
        ),
        (
            """
            [default]
            project = acme
            remote = /project/dir22
            ignore = *.pyc
            """,
            FileConfiguration('acme', '/project/dir22', None, ['*.pyc'])
        ),
        (
            """
            [default]
            project = acme
            remote = /project/dir22
            server = some-server-name
            """,
            FileConfiguration('acme', '/project/dir22', 'some-server-name', [])
        ),
        (
            """
            [default]
            project = acme
            remote = /project/dir22
            ignore = *.pyc, pattern/
            """,
            FileConfiguration(
                'acme', '/project/dir22', None, ['*.pyc', 'pattern/'])
        ),
        (
            """
            [default]
            project = acme
            remote = /project/dir22
            ignore =
            """,
            FileConfiguration(
                'acme', '/project/dir22', None, [])
        ),
    ]
)
def test_project_config(config, expected):
    with _temporary_configurations(project_config=config) as (
            project_path, user_path):
        result = get_config('.', project_path, user_path)
        assert result == expected


def test_project_config_multiple_sections():
    config = """
    [default]
    project = acme

    [other-entry]
    project = something-else
    """
    with _temporary_configurations(project_config=config) as (
             project_path, user_path):
        with pytest.raises(ValueError):
            get_config('.', project_path, user_path)


@pytest.mark.parametrize(
    'local_directory,config,expected',
    [
        (
            LOCAL_DIRECTORY,
            """
            [{}]
            project = acme
            remote = /project/dir22
            """.format(LOCAL_DIRECTORY),
            FileConfiguration('acme', '/project/dir22', None, [])
        ),
        (
            # Test tilde expansion
            LOCAL_DIRECTORY,
            """
            [{}]
            project = acme
            remote = /project/dir22
            """.format(LOCAL_DIRECTORY_WITH_TILDE),
            FileConfiguration('acme', '/project/dir22', None, [])
        )
    ]
)
def test_user_config(local_directory, config, expected):
    with _temporary_configurations(user_config=config) as (
            project_path, user_path):
        result = get_config(local_directory, project_path, user_path)
        assert result == expected


def test_config_present_in_both_user_and_project():
    project_config = """
    [defaut]
    project = acme
    """

    user_config = """
    [{}]
    project = other-project
    """.format(LOCAL_DIRECTORY)
    with _temporary_configurations(user_config, project_config) as (
            project_path, user_path):
        with pytest.raises(ValueError):
            get_config('.', project_path, user_path)


def test_no_config():
    with _temporary_configurations() as (project_path, user_path):
        result = get_config('.', project_path, user_path)
        assert result == FileConfiguration(None, None, None, [])
