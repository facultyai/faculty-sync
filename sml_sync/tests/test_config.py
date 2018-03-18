import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from ..config import get_config, FileConfiguration


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
        result = get_config('local-directory', project_path, user_path)
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
            get_config('local-directory', project_path, user_path)


@pytest.mark.parametrize(
    'local_directory,config,expected',
    [
        (
            '/absolute/path/to/project',
            """
            [/absolute/path/to/project]
            project = acme
            remote = /project/dir22
            """,
            FileConfiguration('acme', '/project/dir22', None, [])
        ),
        (
            os.path.expanduser('~/relative/from/home'),
            """
            [~/relative/from/home]
            project = acme
            remote = /project/dir22
            """,
            FileConfiguration('acme', '/project/dir22', None, [])
        ),
        (
            os.path.expanduser('~/relative/from/home'),
            """
            [~/relative/from/home]
            project = acme
            remote = /project/dir22
            """,
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
    [/path/to/local-directory]
    project = other-project
    """
    with _temporary_configurations(user_config, project_config) as (
            project_path, user_path):
        with pytest.raises(ValueError):
            get_config('/path/to/local-directory', project_path, user_path)
