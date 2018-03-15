from pathlib import Path
import configparser


def get_config(directory: str) -> configparser.ConfigParser:
    """
    Parse a smlsync.conf file.

    The function first checks in the passed directory, and if it doesn't
    find a configuration file, checks if there is one in the user directory.
    """
    directory = Path(directory).expanduser().resolve()

    project_conf_file = directory / '.sml-sync.conf'
    user_conf_file = Path('~/.config/sml-sync/sml-sync.conf').expanduser()

    config = configparser.ConfigParser(
        converters={'list': lambda string, delim=',': [
            s.strip() for s in string.split(delim)
        ]}
    )

    if user_conf_file.exists():
        # read the user conf file
        config.read(user_conf_file)

        # "normalise" the paths to avoid issues with symlinks and ~
        config.read_dict({
            str(Path(key).expanduser().resolve()).rstrip('/'): value
            for key, value in config.items()
            if key.lower() != 'default'
            and not config.has_section(str(Path(key).expanduser()
                                           .resolve()).rstrip('/'))
        })

    if project_conf_file.exists():
        project_config = configparser.ConfigParser(
            converters={'list': lambda string, delim=',': [
                s.strip() for s in string.split(delim)
            ]}
        )
        # read the project conf file
        project_config.read([project_conf_file])
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
        return config[str(directory)]
    else:
        return {}
