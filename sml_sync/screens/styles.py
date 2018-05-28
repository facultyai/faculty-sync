
import sys

from prompt_toolkit.application.current import get_app


def _try_char(character, backup, encoding=sys.stdout.encoding):
    """
    Return `character` if it can be encoded using sys.stdout, else return the
    backup character.
    """
    if character.encode(encoding, 'replace') == b'?':
        return backup
    else:
        return character


def get_vertical_border_char():
    " Return the character to be used for the vertical border. "
    return _try_char('\u2502', '|', get_app().output.encoding())
