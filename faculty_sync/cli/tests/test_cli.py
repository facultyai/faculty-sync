import uuid
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from faculty.clients.project import Project

from ... import cli
from .. import models
from ..config import FileConfiguration


@contextmanager
def _patched_config(config: FileConfiguration):
    with patch.object(cli, "get_config", return_value=config) as mock:
        yield mock


@contextmanager
def _patched_server(server_id: uuid.UUID):
    with patch.object(cli, "resolve_server", return_value=server_id) as mock:
        yield mock


@contextmanager
def _patched_project(project: Project):
    with patch.object(cli, "resolve_project", return_value=project) as mock:
        yield mock


def test_no_args():
    file_config = FileConfiguration(
        "project-name", "/project/remote/dir", None, []
    )
    argv = []
    server_id = uuid.uuid4()
    project = Project(uuid.uuid4(), "project-name", uuid.uuid4())
    with _patched_config(file_config):
        with _patched_server(server_id) as resolve_server_mock:
            with _patched_project(project) as resolve_project_mock:
                configuration = cli.parse_command_line(argv=argv)
                assert configuration == models.Configuration(
                    project=project,
                    server_id=server_id,
                    local_dir="./",
                    remote_dir=file_config.remote + "/",
                    debug=False,
                    ignore=cli.DEFAULT_IGNORE_PATTERNS,
                )

                resolve_project_mock.assert_called_once_with("project-name")
                resolve_server_mock.assert_called_once_with(project.id, None)


def test_override_project():
    file_config = FileConfiguration(
        "project-name", "/project/remote/dir", None, []
    )
    argv = ["--project", "other-project"]
    server_id = uuid.uuid4()
    project = Project(uuid.uuid4(), "other-project", uuid.uuid4())
    with _patched_config(file_config):
        with _patched_server(server_id):
            with _patched_project(project) as resolve_project_mock:
                cli.parse_command_line(argv=argv)
                resolve_project_mock.assert_called_once_with("other-project")


def test_specify_server_configuration():
    file_config = FileConfiguration(
        "project-name", "/project/remote/dir", "server-name", []
    )
    argv = []
    server_id = uuid.uuid4()
    project = Project(uuid.uuid4(), "project-name", uuid.uuid4())
    with _patched_config(file_config):
        with _patched_server(server_id) as resolve_server_mock:
            with _patched_project(project):
                cli.parse_command_line(argv=argv)
                resolve_server_mock.assert_called_once_with(
                    project.id, "server-name"
                )


def test_specify_server_command_line():
    file_config = FileConfiguration(
        "project-name", "/project/remote/dir", None, []
    )
    argv = ["--server", "server-name"]
    server_id = uuid.uuid4()
    project = Project(uuid.uuid4(), "project-name", uuid.uuid4())
    with _patched_config(file_config):
        with _patched_server(server_id) as resolve_server_mock:
            with _patched_project(project):
                cli.parse_command_line(argv=argv)
                resolve_server_mock.assert_called_once_with(
                    project.id, "server-name"
                )


def test_add_ignore():
    file_config = FileConfiguration(
        "project-name", "/project/remote/dir", None, ["ig1"]
    )
    argv = ["--ignore", "ig2", "ig3"]
    server_id = uuid.uuid4()
    project = Project(uuid.uuid4(), "project-name", uuid.uuid4())
    with _patched_config(file_config):
        with _patched_server(server_id):
            with _patched_project(project):
                configuration = cli.parse_command_line(argv=argv)
                expected_ignore_patterns = cli.DEFAULT_IGNORE_PATTERNS + [
                    "ig1",
                    "ig2",
                    "ig3",
                ]
                assert configuration.ignore == expected_ignore_patterns


def test_no_configuration():
    file_config = FileConfiguration(None, None, None, [])
    argv = ["--project", "project-name"]
    server_id = uuid.uuid4()
    project = Project(uuid.uuid4(), "project-name", uuid.uuid4())
    with _patched_config(file_config):
        with _patched_server(server_id):
            with _patched_project(project) as resolve_project_mock:
                configuration = cli.parse_command_line(argv=argv)
                assert configuration == models.Configuration(
                    project=project,
                    server_id=server_id,
                    local_dir="./",
                    remote_dir=None,
                    debug=False,
                    ignore=cli.DEFAULT_IGNORE_PATTERNS,
                )

                resolve_project_mock.assert_called_once_with("project-name")


def test_no_configuration_no_project():
    file_config = FileConfiguration(None, None, None, [])
    argv = []
    with _patched_config(file_config):
        with pytest.raises(ValueError):
            cli.parse_command_line(argv=argv)
