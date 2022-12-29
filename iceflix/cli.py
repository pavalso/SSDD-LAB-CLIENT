"""Submodule containing the CLI command handlers."""

import logging

from iceflix.client import client_main


LOG_FORMAT = '%(asctime)s - %(levelname)-7s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'


def setup_logging():
    """Configure the logging."""
    logging.basicConfig(
        level=logging.DEBUG,
        format=LOG_FORMAT,
    )

def client():
    """Handles the IceFlix client CLI command."""
    setup_logging()
    logging.info("Starting IceFlix client...")
    client_main()
    return 0

def main():
    """Handles the IceFlix client CLI command."""
    from iceflix.main import MainApp
    import sys
    setup_logging()
    logging.info("Starting IceFlix main...")
    MainApp().main(sys.argv)
    return 0

def authenticator():
    from iceflix.authenticator import AuthenticatorApp
    import sys
    setup_logging()
    logging.info("Starting IceFlix authenticator...")
    AuthenticatorApp().main(sys.argv)
    return 0