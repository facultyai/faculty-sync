
from typing import Optional

from .document import Document


class Buffer(object):

    def __init__(
            self,
            document: Optional[Document] = None,
            read_only: bool = False
    ) -> None: ...
