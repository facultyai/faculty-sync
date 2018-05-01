import textwrap

import pytest

from .. import Table, TableColumn


def test_simple_table():
    col1 = TableColumn(rows=['a', 'b', 'c'], header='t1')
    col2 = TableColumn(rows=['d', 'e', 'f'], header='t2')

    table = Table([col1, col2])

    assert table._header_control.text == 't1 t2'
    assert table._body_control.buffer.text == textwrap.dedent(
        """\
        a  d 
        b  e 
        c  f """)  # noqa: W291 (ignore trailing whitespace)


def test_table_varying_row_lengths():
    col1 = TableColumn(rows=['a', 'some-long-value'], header='t1')
    col2 = TableColumn(rows=['long', 'b'], header='t2')

    table = Table([col1, col2])

    assert table._header_control.text == textwrap.dedent("""\
        t1              t2  """)
    assert table._body_control.buffer.text == textwrap.dedent(
        """\
        a               long
        some-long-value b   """)


def test_different_length_rows():
    col1 = TableColumn(rows=['a', 'b', 'c'], header='t1')
    col2 = TableColumn(rows=['e'], header='t2')

    with pytest.raises(ValueError):
        Table([col1, col2])


def test_no_rows():
    col1 = TableColumn(rows=[], header='t1')
    col2 = TableColumn(rows=[], header='t2')

    table = Table([col1, col2])

    assert table._header_control.text == 't1 t2'
    assert table._body_control.buffer.text == ''


def test_no_columns():
    table = Table([])

    assert table._header_control.text == ''
    assert table._body_control.buffer.text == ''
