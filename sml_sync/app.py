
import logging

import daiquiri

from .cli import parse_command_line
from .controller import Controller
from .pubsub import PubSubExchange
from .ssh import get_ssh_details
from .ui import View


def run():
    try:
        configuration = parse_command_line()
    except Exception as e:
        print(e)
        exit(1)

    daiquiri.setup(
        level=logging.INFO if configuration.debug else logging.ERROR,
        outputs=[daiquiri.output.File('/tmp/sml-sync.log')]
    )

    logging.info(
        'sml-sync started with configuration {}'.format(configuration))

    exchange = PubSubExchange()
    exchange.start()
    view = View(configuration, exchange)
    view.start()

    with get_ssh_details(configuration) as ssh_details:
        controller = Controller(configuration, ssh_details, view, exchange)
        controller.start()

        # Run until the controller stops
        controller.join()

    view.stop()
    exchange.stop()
    exchange.join()
