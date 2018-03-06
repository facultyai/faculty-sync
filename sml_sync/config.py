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

    config = configparser.ConfigParser()
    config.read([project_conf_file, user_conf_file])
    config = config._sections  # convert to normal dict

    # convert ignores to list
    for section in config.keys():
        if "ignore" in config[section]:
            config[section]["ignore"] = [
                s.strip() for s in config[section]["ignore"].split(',')
            ]

    # "normalise" the paths to avoid issues with symlinks and ~
    config.update(**{
        str(Path(key).expanduser().resolve()).rstrip('/'): value
        for key, value in config.items()
    })

    if str(directory) in config:
        return config[str(directory)]
    else:
        return {}
