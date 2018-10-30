from pathlib import Path
import configparser
from typing import NamedTuple, List, Optional


FileConfiguration = NamedTuple(
    'FileConfiguration',
    [
        ('project', Optional[str]),
        ('remote', Optional[str]),
        ('server', Optional[str]),
        ('ignore', List[str]),
    ],
)


def _empty_file_configuration():
    return FileConfiguration(None, None, None, [])


def _read_ignore_patterns(ignore_string: str) -> List[str]:
    return [s.strip() for s in ignore_string.split(',') if s.strip()]


def _create_parser():
    converters = {'list': _read_ignore_patterns}
    return configparser.ConfigParser(converters=converters)


def get_config(
    local_directory: str, project_conf_path=None, user_conf_path=None
) -> FileConfiguration:
    """
    Parse a sml-sync.conf file.

    The function first checks in the passed directory, and if it doesn't
    find a configuration file, checks if there is one in the user directory.
    """
    directory = Path(local_directory).expanduser().resolve()

    if project_conf_path is None:
        project_conf_path = directory / '.sml-sync.conf'
    if user_conf_path is None:
        user_conf_path = Path('~/.config/sml-sync/sml-sync.conf')
    user_conf_path = user_conf_path.expanduser()

    config = _create_parser()

    try:
        with user_conf_path.open() as fp:
            config.read_file(fp)

            # "normalise" the paths to avoid issues with symlinks and ~
            config.read_dict(
                {
                    str(Path(key).expanduser()).rstrip('/'): value
                    for key, value in config.items()
                    if key.lower() != 'default'
                    and not config.has_section(
                        str(Path(key).expanduser()).rstrip('/')
                    )
                }
            )
    except FileNotFoundError:
        pass

    try:
        project_config = _create_parser()
        with project_conf_path.open() as fp:
            project_config.read_file(fp)
            if len(project_config.sections()) > 1:
                raise ValueError(
                    'The project config file is ambiguous, as it has '
                    'more than two sections.'
                )
            elif len(project_config.sections()) == 1:
                if str(directory) in config:
                    raise ValueError(
                        'You can\'t specify configurations for a '
                        'project in both the home and project '
                        'directory.'
                    )
                config.read_dict(
                    {
                        str(directory): project_config[
                            project_config.sections()[0]
                        ]
                    }
                )
    except FileNotFoundError:
        pass

    if str(directory) in config:
        section = config[str(directory)]
        ignore = section.getlist('ignore')
        if ignore is None:
            ignore = []
        parsed_configuration = FileConfiguration(
            project=section.get('project'),
            remote=section.get('remote'),
            server=section.get('server'),
            ignore=ignore,
        )
    else:
        parsed_configuration = _empty_file_configuration()
    return parsed_configuration
