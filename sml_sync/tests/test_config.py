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
