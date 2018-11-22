from collections import namedtuple
import itertools
from enum import Enum
from typing import List, Optional

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout import (
    Window,
    HSplit,
    FormattedTextControl,
    BufferControl,
    ScrollbarMargin,
)


class Alignment(Enum):
    RIGHT = "RIGHT"
    LEFT = "LEFT"


class ColumnSettings(object):
    def __init__(self, alignment=Alignment.LEFT):
        self.alignment = alignment


class TableColumn(namedtuple("Column", ["rows", "header", "settings"])):
    def __new__(
        cls,
        rows: List[str],
        header: str,
        settings: Optional[ColumnSettings] = None,
    ):
        if settings is None:
            settings = ColumnSettings()
        return super(TableColumn, cls).__new__(cls, rows, header, settings)


class Table(object):
    def __init__(self, columns: List[TableColumn], sep: str = " "):
        if len({len(column.rows) for column in columns}) not in {0, 1}:
            raise ValueError("All columns must have the same number of rows.")

        self._sep = sep

        formatted_headers = []
        formatted_columns = []
        for column in columns:
            width = self._get_column_width(column)
            formatted_rows = [
                self._format_cell(row, column.settings, width)
                for row in column.rows
            ]
            formatted_headers.append(column.header.ljust(width, " "))
            formatted_columns.append(formatted_rows)

        self.window = HSplit(
            self._header_windows(formatted_headers)
            + self._body_windows(formatted_columns)
        )

    def _get_column_width(self, column):
        width = max(
            len(column.header),
            max((len(row) for row in column.rows), default=0),
        )
        return width

    def _format_cell(self, content, column_settings, width):
        if column_settings.alignment == Alignment.LEFT:
            return content.ljust(width)
        else:
            return content.rjust(width)

    def _header_windows(self, formatted_headers):
        if len(formatted_headers):
            header_control = FormattedTextControl(
                self._sep.join(formatted_headers)
            )
            header_windows = [Window(header_control, height=1)]
        else:
            header_windows = [Window(height=1, width=0)]
        return header_windows

    def _body_windows(self, formatted_columns):
        rows = list(itertools.zip_longest(*formatted_columns, fillvalue=""))
        if rows:
            rows_string = [self._sep.join(row) for row in rows]
            table_body = "\n".join(rows_string)

            document = Document(table_body, 0)
            _buffer = Buffer(document=document, read_only=True)
            self._body_control = BufferControl(_buffer)
            body_windows = [
                Window(
                    self._body_control,
                    right_margins=[ScrollbarMargin(display_arrows=True)],
                )
            ]
        else:
            body_windows = []
        return body_windows

    def preferred_width(self, max_available_width):
        return self.window.preferred_width(max_available_width)

    def preferred_height(self, width, max_available_height):
        return self.window.preferred_height(width, max_available_height)

    def write_to_screen(self, *args, **kwargs):
        return self.window.write_to_screen(*args, **kwargs)

    def get_children(self):
        return self.window.get_children()

    def __pt_container__(self):
        return self.window
