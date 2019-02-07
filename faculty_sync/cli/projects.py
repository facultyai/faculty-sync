import uuid

import faculty


def resolve_project(project):
    """Resolve a project name or ID to a project ID."""
    projects_client = faculty.client("project")
    try:
        project_id = uuid.UUID(project)
        project = projects_client.get(project_id)
    except ValueError:
        account_client = faculty.client("account")
        user_id = account_client.authenticated_user_id()
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
