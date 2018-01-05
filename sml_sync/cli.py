
import uuid
import argparse

import sml.auth
import sml.casebook

from .models import Configuration
from .projects import Project, Projects


class NoValidServer(Exception):
    pass


def parse_command_line(argv=None):
    parser = argparse.ArgumentParser(
        description='Autosync a local directory to a SherlockML project'
    )
    parser.add_argument('project', help='Project name or ID')
    parser.add_argument(
        'remote',
        help='Remote directory, e.g. /project/src'
    )
    parser.add_argument(
        '--local',
        default='.',
        help='Local directory to sync from'
    )
    arguments = parser.parse_args(argv)
    project = _resolve_project(arguments.project)
    server_id = _any_server(project.id_)
    local_dir = arguments.local
    remote_dir = arguments.remote
    local_dir = local_dir.rstrip('/') + '/'
    remote_dir = remote_dir.rstrip('/') + '/'
    configuration = Configuration(
        project, server_id, local_dir, remote_dir
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
