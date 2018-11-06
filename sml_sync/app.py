import logging

from .cli import parse_command_line
from .controller import Controller
from .pubsub import PubSubExchange
from .ssh import get_ssh_details
from .ui import View
from .update import check_for_new_release
from .logs import setup_logging


def run():
    try:
        configuration = parse_command_line()
    except Exception as e:
        print(e)
        exit(1)

    setup_logging(configuration.debug)

    logging.info(
        "sml-sync started with configuration {}".format(configuration)
    )

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

    check_for_new_release()
