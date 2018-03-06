from pathlib import Path
import configparser


def get_config(directory: str) -> configparser.ConfigParser:
    """
    Parse a smlsync.conf file.

    The function first checks in the passed directory, and if it doesn't
    find a configuration file, checks if there is one in the user directory.
    """
    directory = Path(directory).expanduser().resolve()

    project_conf_file = directory / "smlsync.conf"
    user_conf_file = Path("~/.config/sherlockml/smlsync.conf").expanduser()

    config = configparser.ConfigParser(
        converters={'list': lambda string, delim=",": [
            s.strip() for s in string.split(delim)
        ]}
    )
    config.read([project_conf_file, user_conf_file])

    # "normalise" the paths to avoid issues with symlinks and ~
    config.read_dict({
        str(Path(key).expanduser().resolve()).rstrip('/'): value
        for key, value in config.items()
        if key.lower() != "default"
    })

    if str(directory) in config:
        return config[str(directory)]
    else:
        return {}
