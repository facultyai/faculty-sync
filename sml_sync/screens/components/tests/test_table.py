import textwrap

import pytest

from .. import Table, TableColumn


def test_simple_table():
    col1 = TableColumn(rows=['a', 'b', 'c'], header='t1')
    col2 = TableColumn(rows=['d', 'e', 'f'], header='t2')

    table = Table([col1, col2])

    assert len(table.window.children) == 2
    [header_window, body_window] = table.window.children

    assert header_window.content.text == 't1 t2'
    assert body_window.content.buffer.text == textwrap.dedent(
        """\
        a  d 
        b  e 
        c  f """)  # noqa: W291 (ignore trailing whitespace)
    assert table.preferred_width(100).preferred == 5
    assert table.preferred_height(5, 100).preferred == 4


def test_table_varying_row_lengths():
    col1 = TableColumn(rows=['a', 'some-long-value'], header='t1')
    col2 = TableColumn(rows=['long', 'b'], header='t2')

    table = Table([col1, col2])

    assert len(table.window.children) == 2
    [header_window, body_window] = table.window.children

    assert header_window.content.text == textwrap.dedent("""\
        t1              t2  """)
    assert body_window.content.buffer.text == textwrap.dedent(
        """\
        a               long
        some-long-value b   """)
    assert table.preferred_width(100).preferred == 20
    assert table.preferred_height(5, 100).preferred == 3


def test_different_length_rows():
    col1 = TableColumn(rows=['a', 'b', 'c'], header='t1')
    col2 = TableColumn(rows=['e'], header='t2')

    with pytest.raises(ValueError):
        Table([col1, col2])


def test_no_rows():
    col1 = TableColumn(rows=[], header='t1')
    col2 = TableColumn(rows=[], header='t2')

    table = Table([col1, col2])

    assert len(table.window.children) == 1
    [header_window] = table.window.children

    assert header_window.content.text == 't1 t2'
    assert table.preferred_width(100).preferred == 5
    assert table.preferred_height(5, 100).preferred == 1


def test_no_columns():
    table = Table([])

    assert len(table.window.children) == 1

    assert table.preferred_width(100).preferred == 0
    assert table.preferred_height(0, 100).preferred == 1


def test_custom_separator():
    col1 = TableColumn(rows=['a', 'b', 'c'], header='t1')
    col2 = TableColumn(rows=['d', 'e', 'f'], header='t2')

    table = Table([col1, col2], sep=' | ')

    assert len(table.window.children) == 2
    [header_window, body_window] = table.window.children

    assert header_window.content.text == 't1 | t2'
    assert body_window.content.buffer.text == textwrap.dedent(
        """\
        a  | d 
        b  | e 
        c  | f """)  # noqa: W291 (ignore trailing whitespace)
    assert table.preferred_width(100).preferred == 7
    assert table.preferred_height(5, 100).preferred == 4
