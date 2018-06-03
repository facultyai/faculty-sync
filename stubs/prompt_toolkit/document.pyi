
from typing import Optional


class Document(object):

    def __init__(
            self,
            text: str = '',
            cursor_position: Optional[int] = None) -> None: ...
