
from prompt_toolkit.layout import to_container
from prompt_toolkit.key_binding.key_processor import KeyProcessor, KeyPress

from .. import VerticalMenu, MenuEntry


def test_simple_menu():
    entry1 = MenuEntry(1, 'menu entry 1')
    entry2 = MenuEntry(2, 'menu entry 2')

    menu = VerticalMenu([entry1, entry2])

    menu_text = to_container(menu).content.text
    assert len(menu_text) == 2
    [menu_line1, menu_line2] = menu_text
    assert menu_line1 == ('reverse', 'menu entry 1\n')
    assert menu_line2 == ('', 'menu entry 2\n')


def test_change_entry():
    entry1 = MenuEntry(1, 'menu entry 1')
    entry2 = MenuEntry(2, 'menu entry 2')

    menu = VerticalMenu([entry1, entry2])

    control = to_container(menu).content
    key_bindings = control.key_bindings
    key_processor = KeyProcessor(key_bindings)
    key_processor.feed(KeyPress('up'))
    key_processor.process_keys()

    menu_text = to_container(menu).content.text

    assert len(menu_text) == 2
    [menu_line1, menu_line2] = menu_text
    assert menu_line1 == ('', 'menu entry 1\n')
    assert menu_line2 == ('reverse', 'menu entry 2\n')

    assert menu.current_selection == 2
