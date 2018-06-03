from unittest.mock import Mock

from prompt_toolkit.layout import to_container
from prompt_toolkit.key_binding.key_processor import KeyProcessor, KeyPress

from .. import VerticalMenu, MenuEntry


def get_menu_text(menu):
    """ Get the formatted text corresponding to the menu """
    control = to_container(menu).content
    return control.text


def simulate_key(menu, key):
    """ Simulate passing `key` to a menu """
    control = to_container(menu).content
    key_bindings = control.key_bindings
    key_processor = KeyProcessor(key_bindings)
    key_processor.feed(KeyPress(key))
    key_processor.process_keys()


def test_simple_menu():
    entry1 = MenuEntry(1, 'menu entry 1')
    entry2 = MenuEntry(2, 'menu entry 2')

    menu = VerticalMenu([entry1, entry2])

    menu_text = get_menu_text(menu)
    assert len(menu_text) == 2
    [menu_line1, menu_line2] = menu_text
    assert menu_line1 == ('reverse', 'menu entry 1\n')
    assert menu_line2 == ('', 'menu entry 2\n')


def test_key_down():
    entry1 = MenuEntry(1, 'menu entry 1')
    entry2 = MenuEntry(2, 'menu entry 2')

    menu = VerticalMenu([entry1, entry2])

    simulate_key(menu, 'down')

    menu_text = get_menu_text(menu)
    assert len(menu_text) == 2
    [menu_line1, menu_line2] = menu_text
    assert menu_line1 == ('', 'menu entry 1\n')
    assert menu_line2 == ('reverse', 'menu entry 2\n')

    assert menu.current_selection == 2


def test_key_up():
    entry1 = MenuEntry(1, 'menu entry 1')
    entry2 = MenuEntry(2, 'menu entry 2')

    menu = VerticalMenu([entry1, entry2])

    simulate_key(menu, 'down')
    simulate_key(menu, 'up')

    menu_text = get_menu_text(menu)
    assert len(menu_text) == 2
    [menu_line1, menu_line2] = menu_text
    assert menu_line1 == ('reverse', 'menu entry 1\n')
    assert menu_line2 == ('', 'menu entry 2\n')

    assert menu.current_selection == 1


def test_wrap_keys():
    entry1 = MenuEntry(1, 'menu entry 1')
    entry2 = MenuEntry(2, 'menu entry 2')

    menu = VerticalMenu([entry1, entry2])

    simulate_key(menu, 'down')
    simulate_key(menu, 'down')

    menu_text = get_menu_text(menu)
    assert len(menu_text) == 2
    [menu_line1, menu_line2] = menu_text
    assert menu_line1 == ('reverse', 'menu entry 1\n')
    assert menu_line2 == ('', 'menu entry 2\n')

    assert menu.current_selection == 1


def test_callback_called():
    mock_callback = Mock()

    entry1 = MenuEntry(1, 'menu entry 1')
    entry2 = MenuEntry(2, 'menu entry 2')

    menu = VerticalMenu([entry1, entry2])

    menu.register_menu_change_callback(mock_callback)

    simulate_key(menu, 'down')

    mock_callback.assert_called_with(2)


def test_zero_entries():
    menu = VerticalMenu([])
    menu_text = get_menu_text(menu)
    assert len(menu_text) == 0
    assert menu.current_selection is None
    simulate_key(menu, 'up')
    assert menu.current_selection is None


def test_single_entry():
    menu = VerticalMenu([MenuEntry('only', 'menu entry')])
    menu_text = get_menu_text(menu)
    assert len(menu_text) == 1
    [menu_line1] = menu_text
    assert menu_line1 == ('reverse', 'menu entry\n')
    assert menu.current_selection == 'only'
    simulate_key(menu, 'up')

    menu_text = get_menu_text(menu)
    assert len(menu_text) == 1
    [menu_line1] = menu_text
    assert menu_line1 == ('reverse', 'menu entry\n')
    assert menu.current_selection == 'only'


def test_different_entry_widths():
    entry1 = MenuEntry(1, 'short')
    entry2 = MenuEntry(2, 'very long entry')

    menu = VerticalMenu([entry1, entry2])
    menu_text = get_menu_text(menu)

    assert len(menu_text) == 2
    [menu_line1, menu_line2] = menu_text
    assert menu_line1 == ('reverse', 'short\n')
    assert menu_line2 == ('', 'very long entry\n')

    width = to_container(menu).preferred_width(100)
    assert width.preferred == 15
    assert width.min == 0
    assert width.max > 100


def test_fixed_width():
    entry1 = MenuEntry(1, 'short')
    entry2 = MenuEntry(2, 'very long entry')

    menu = VerticalMenu([entry1, entry2], width=8)
    menu_text = get_menu_text(menu)

    assert len(menu_text) == 2
    [menu_line1, menu_line2] = menu_text
    assert menu_line1 == ('reverse', 'short   \n')
    assert menu_line2 == ('', 'very lon\n')

    width = to_container(menu).preferred_width(100)
    assert width.preferred == 8
    assert width.min == width.max == 8
