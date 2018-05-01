from collections import namedtuple
import itertools
from typing import List

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout import (
    Window, HSplit, FormattedTextControl, BufferControl, ScrollbarMargin)


TableColumn = namedtuple('Column', ['rows', 'header'])


class Table(object):

    def __init__(self, columns: List[TableColumn]):
        formatted_headers = []
        formatted_columns = []
        for column in columns:
            width = max(
                    len(column.header),
                    max(len(row) for row in column.rows)
            )
            formatted_rows = [row.ljust(width, ' ') for row in column.rows]
            formatted_headers.append(column.header.ljust(width, ' '))
            formatted_columns.append(formatted_rows)

        rows = list(
            itertools.zip_longest(*formatted_columns, fillvalue='')
        )

        rows_string = [' '.join(row) for row in rows]
        table_body = '\n'.join(rows_string)

        self._header_control = FormattedTextControl(
            ' '.join(formatted_headers))

        document = Document(table_body, 0)
        _buffer = Buffer(document=document, read_only=True)
        self._body_control = BufferControl(_buffer)

        self.window = HSplit([
            Window(self._header_control, height=1),
            Window(
                self._body_control,
                right_margins=[ScrollbarMargin(display_arrows=True)]
            )
        ])

    def __pt_container__(self):
        return self.window
