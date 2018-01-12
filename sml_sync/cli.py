
import uuid
import argparse

import sml.auth
import sml.casebook

from .models import Configuration
from .projects import Projects


class NoValidServer(Exception):
    pass


def parse_command_line(argv=None):
    parser = argparse.ArgumentParser(
        description='Autosync a local directory to a SherlockML project'
    )
    parser.add_argument('project', help='Project name or ID')
    parser.add_argument(
        '--remote',
        default=None,
        help=(
            'Remote directory, e.g. /project/src. If omitted, '
            'you will be prompted for a directory.')
    )
    parser.add_argument(
        '--local',
        default='.',
        help='Local directory to sync from. Defaults to the current directory.'
    )
    parser.add_argument(
        '--ignore',
        nargs='+',
        help='Path fragments to ignore (e.g. node_modules, __pycache__).'
    )
    parser.add_argument(
        '--debug',
        default=False,
        action='store_true',
        help='Run in debug mode (sets the log level to info).'
    )
    arguments = parser.parse_args(argv)
    project = _resolve_project(arguments.project)
    server_id = _any_server(project.id_)
    local_dir = arguments.local
    remote_dir = arguments.remote
    local_dir = local_dir.rstrip('/') + '/'
    if remote_dir is not None:
        remote_dir = remote_dir.rstrip('/') + '/'
    configuration = Configuration(
        project, server_id, local_dir, remote_dir,
        arguments.debug, arguments.ignore
    )
    return configuration


def _resolve_project(project):
    """Resolve a project name or ID to a project ID."""
    projects_client = Projects()
    try:
        project_id = uuid.UUID(project)
        project = projects_client.get_project_by_id(project_id)
    except ValueError:
        user_id = sml.auth.user_id()
        project = projects_client.get_project_by_name(
            user_id, project)
    return project


def _any_server(project_id, status=None):
    """Get any running server from project."""
    client = sml.galleon.Galleon()
    servers_ = client.get_servers(project_id, status=status)
    if not servers_:
        adjective = 'available' if status is None else status
        message = 'No {} server in project.'.format(adjective)
        raise NoValidServer(message)
    return servers_[0].id_
