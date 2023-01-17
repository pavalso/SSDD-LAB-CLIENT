"""Submodule containing the CLI command handlers."""

import argparse
import logging

from iceflix.client import client_main


LOG_FORMAT = '%(asctime)s - %(levelname)-7s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'

VERBOSITY_LEVELS = {
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
}

def setup_logging():
    """Configure the logging."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbosity', action="count",
        help="increase output verbosity (e.g., -vv is more than -v)",
        default=0)
    args, _ = parser.parse_known_args()
    level = VERBOSITY_LEVELS.get(args.verbosity, logging.NOTSET)
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
    )

def client():
    """Handles the IceFlix client CLI command."""
    setup_logging()
    logging.info("Starting IceFlix client...")
    client_main()
    return 0

#import sys
#
#def main():
#    """Handles the IceFlix client CLI command."""
#    from iceflix.main import MainApp
#    setup_logging()
#    logging.info("Starting IceFlix main...")
#    MainApp().main(sys.argv)
#    return 0
#
#def authenticator():
#    from iceflix.authenticator import AuthenticatorApp
#    setup_logging()
#    logging.info("Starting IceFlix authenticator...")
#    AuthenticatorApp().main(sys.argv)
#    return 0
#
#def catalog():
#    from iceflix.catalog import CatalogApp
#    setup_logging()
#    logging.info("Starting IceFlix catalog...")
#    CatalogApp().main(sys.argv)
#    return 0
#
#def fileservice():
#    from iceflix.file_service import FileServiceApp
#    setup_logging()
#    logging.info("Starting IceFlix FileService...")
#    FileServiceApp().main(sys.argv)
#    return 0
#
