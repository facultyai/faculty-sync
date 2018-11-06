import argparse
from pathlib import Path

from .models import Configuration
from .projects import resolve_project
from ..version import version
from .config import get_config
from .servers import resolve_server


DEFAULT_IGNORE_PATTERNS = [
    "node_modules",
    "__pycache__",
    "*.pyc",
    ".ipynb_checkpoints",
    ".tox",
    ".git",
    ".mypy_cache",
    ".cache",
]


def parse_command_line(argv=None):
    parser = argparse.ArgumentParser(
        prog="sml-sync",
        description="Autosync a local directory to a SherlockML project",
    )
    parser.add_argument(
        "--project",
        default=None,
        help=(
            "Project name or ID. If omitted, it has to be present "
            "in the configuration file."
        ),
    )
    parser.add_argument(
        "--remote",
        default=None,
        help=(
            "Remote directory, e.g. /project/src. If omitted, sml-sync "
            "will look first in configuration and, failing that, will "
            "prompt for a directory."
        ),
    )
    parser.add_argument(
        "--local",
        default=".",
        help="Local directory to sync from. Defaults to the current directory.",
    )
    parser.add_argument(
        "--ignore",
        nargs="+",
        help="Path fragments to ignore (e.g. node_modules, __pycache__).",
    )
    parser.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help="Run in debug mode (sets the log level to info).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="sml-sync {version}".format(version=version),
    )
    parser.add_argument(
        "--server",
        default=None,
        help=(
            "The name or ID of the server in the project to use. If omitted,"
            " a random server is used."
        ),
    )
    arguments = parser.parse_args(argv)

    local_dir = arguments.local.rstrip("/") + "/"

    local_path = Path(local_dir).resolve()
    if local_path == Path.home():
        raise ValueError("Synchronising your home directory is not supported.")
    elif local_path == Path("/"):
        raise ValueError("Synchronising your root directory is not supported.")

    config = get_config(local_dir)

    project = arguments.project
    if project is None:
        project = config.project
    if project is None:
        raise ValueError(
            "You have to specify a project either "
            "as an argument, or in the config."
        )
    project = resolve_project(project)

    server = arguments.server
    if server is None:
        server = config.server
    server_id = resolve_server(project.id_, server)

    remote_dir = arguments.remote
    if remote_dir is None:
        remote_dir = config.remote

    if remote_dir is not None:
        remote_dir = remote_dir.rstrip("/") + "/"

    ignore = DEFAULT_IGNORE_PATTERNS + config.ignore
    if arguments.ignore is not None:
        ignore += arguments.ignore

    configuration = Configuration(
        project, server_id, local_dir, remote_dir, arguments.debug, ignore
    )
    return configuration
