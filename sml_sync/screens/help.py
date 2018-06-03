
from prompt_toolkit.layout import HSplit, Window, FormattedTextControl, Float
from prompt_toolkit.widgets import Frame


def help_modal(title, text):
    help_container = Float(Frame(
        HSplit([
            Window(
                FormattedTextControl(title),
                height=1, style='reverse'
            ),
            Window(height=1),
            Window(FormattedTextControl(text)),
            Window(
                FormattedTextControl('[?] Close this window'),
                height=1, style='reverse'
            )
        ])
    ))
    return help_container
