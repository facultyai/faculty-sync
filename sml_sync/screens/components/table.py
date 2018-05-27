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
        if len(set(len(column.rows) for column in columns)) not in {0, 1}:
            raise ValueError('All columns must have the same number of rows.')

        formatted_headers = []
        formatted_columns = []
        for column in columns:
            width = max(
                    len(column.header),
                    max((len(row) for row in column.rows), default=0)
            )
            formatted_rows = [row.ljust(width, ' ') for row in column.rows]
            formatted_headers.append(column.header.ljust(width, ' '))
            formatted_columns.append(formatted_rows)

        rows = list(
            itertools.zip_longest(*formatted_columns, fillvalue='')
        )

        rows_string = [' '.join(row) for row in rows]
        table_body = '\n'.join(rows_string)

        if rows:
            document = Document(table_body, 0)
            _buffer = Buffer(document=document, read_only=True)
            self._body_control = BufferControl(_buffer)
            body_windows = [
                Window(
                    self._body_control,
                    right_margins=[ScrollbarMargin(display_arrows=True)]
                )
            ]
        else:
            body_windows = []

        self.window = HSplit(
            self._header_windows(formatted_headers) + body_windows
        )

    def _header_windows(self, formatted_headers):
        if len(formatted_headers):
            header_control = FormattedTextControl(
                ' '.join(formatted_headers))
            header_windows = [Window(header_control, height=1)]
        else:
            header_windows = [Window(height=1, width=0)]
        return header_windows

    def preferred_width(self, max_available_width):
        return self.window.preferred_width(max_available_width)

    def preferred_height(self, width, max_available_height):
        return self.window.preferred_height(width, max_available_height)

    def __pt_container__(self):
        return self.window
