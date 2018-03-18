
import uuid
from contextlib import contextmanager
from unittest.mock import patch

from .. import cli
from ..config import FileConfiguration
from ..projects import Project


@contextmanager
def _patched_config(config: FileConfiguration):
    with patch.object(cli, 'get_config', return_value=config) as mock:
        yield mock


@contextmanager
def _patched_server(server_id: uuid.UUID):
    with patch.object(cli, 'resolve_server', return_value=server_id) as mock:
        yield mock


@contextmanager
def _patched_project(project: Project):
    with patch.object(cli, 'resolve_project', return_value=project) as mock:
        yield mock


def test_no_args():
    config = FileConfiguration(
        'project-name',
        '/project/remote/dir',
        None,
        []
    )
    server_id = uuid.uuid4()
    project = Project(
        uuid.uuid4(),
        'project-name',
        uuid.uuid4()
    )
    with _patched_config(config):
        with _patched_server(server_id) as resolve_server_mock:
            with _patched_project(project) as resolve_project_mock:
                configuration = cli.parse_command_line(argv=[])
                assert configuration.project == project
                assert configuration.server_id == server_id
                assert configuration.local_dir == './'
                assert configuration.remote_dir == configuration.remote_dir
                assert not configuration.debug
                assert configuration.ignore == cli.DEFAULT_IGNORE_PATTERNS

                resolve_project_mock.assert_called_once_with('project-name')
                resolve_server_mock.assert_called_once_with(
                    project.id_, None)
