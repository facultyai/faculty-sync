import uuid

import sml.auth
import sml.casebook


class NoValidServer(Exception):
    pass


def resolve_server(project_id, server=None, ensure_running=True):
    """Resolve project and server names to project and server IDs."""
    status = 'running' if ensure_running else None
    try:
        server_id = uuid.UUID(server)
    except ValueError:
        server_id = _server_by_name(project_id, server, status).id_
    except TypeError:
        server_id = _any_server(project_id, status)
    return server_id


def _server_by_name(project_id, server_name, status=None):
    """Resolve a project ID and server name to a server ID."""
    client = sml.galleon.Galleon()
    matching_servers = client.get_servers(project_id, server_name, status)
    if len(matching_servers) == 1:
        return matching_servers[0]
    else:
        if not matching_servers:
            tpl = 'no {} server of name "{}" in this project'
        else:
            tpl = ('more than one {} server of name "{}", please select by '
                   'server ID instead')
        adjective = 'available' if status is None else status
        raise NoValidServer(tpl.format(adjective, server_name))


def _any_server(project_id, status=None):
    """Get any running server from project."""
    client = sml.galleon.Galleon()
    servers_ = client.get_servers(project_id, status=status)
    if not servers_:
        adjective = 'available' if status is None else status
        message = 'No {} server in project.'.format(adjective)
        raise NoValidServer(message)
    return servers_[0].id_
