import uuid

import faculty
import faculty_cli.auth


def resolve_project(project):
    """Resolve a project name or ID to a project ID."""
    projects_client = faculty.client("project")
    try:
        project_id = uuid.UUID(project)
        project = projects_client.get(project_id)
    except ValueError:
        user_id = faculty_cli.auth.user_id()
        projects = [
            p
            for p in projects_client.list_accessible_by_user(user_id)
            if p.name == project
        ]
        if len(projects) == 1:
            project = projects[0]
        else:
            raise ValueError("Could not resolve project.")
    return project
