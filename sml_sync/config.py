from pathlib import Path
import configparser
from typing import NamedTuple, List, Optional


FileConfiguration = NamedTuple(
    'FileConfiguration',
    [
        ('project', Optional[str]),
        ('remote', Optional[str]),
        ('server', Optional[str]),
        ('ignore', List[str])
    ]
)


def empty_file_configuration():
    return FileConfiguration(None, None, None, [])


def get_config(
        local_directory: str,
        project_conf_path=None,
        user_conf_path=None) -> FileConfiguration:
    """
    Parse a smlsync.conf file.

    The function first checks in the passed directory, and if it doesn't
    find a configuration file, checks if there is one in the user directory.
    """
    directory = Path(local_directory).expanduser().resolve()

    if project_conf_path is None:
        project_conf_path = directory / '.sml-sync.conf'
    if user_conf_path is None:
        user_conf_path = Path('~/.config/sml-sync/sml-sync.conf')
    user_conf_path = user_conf_path.expanduser()

    config = configparser.ConfigParser(
        converters={'list': lambda string, delim=',': [
            s.strip() for s in string.split(delim) if s.strip()
        ]}
    )

    if user_conf_path.exists():
        # read the user conf file
        config.read(user_conf_path)

        # "normalise" the paths to avoid issues with symlinks and ~
        config.read_dict({
            str(Path(key).expanduser().resolve()).rstrip('/'): value
            for key, value in config.items()
            if key.lower() != 'default'
            and not config.has_section(str(Path(key).expanduser()
                                           .resolve()).rstrip('/'))
        })

    if project_conf_path.exists():
        project_config = configparser.ConfigParser(
            converters={'list': lambda string, delim=',': [
                s.strip() for s in string.split(delim) if s.strip()
            ]}
        )
        # read the project conf file
        project_config.read([project_conf_path])
        if len(project_config.sections()) > 1:
            raise ValueError('The project config file is ambiguous, as it has '
                             'more than two sections.')
        elif len(project_config.sections()) == 1:
            if str(directory) in config:
                raise ValueError('You can\'t specify configurations for a '
                                 'project in both the home and project '
                                 'directory.')
            config.read_dict({
                str(directory): project_config[project_config.sections()[0]]
            })

    if str(directory) in config:
        section = config[str(directory)]
        ignore = section.getlist('ignore')
        if ignore is None:
            ignore = []
        parsed_configuration = FileConfiguration(
            project=section.get('project'),
            remote=section.get('remote'),
            server=section.get('server'),
            ignore=ignore
        )
    else:
        parsed_configuration = empty_file_configuration()
    return parsed_configuration
