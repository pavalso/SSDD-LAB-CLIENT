"""Submodule containing the CLI command handlers."""

import logging
import sys

from iceflix.main import MainApp
from iceflix.authenticator import AuthenticatorApp
from iceflix.catalog import MediaCatalogApp
#from iceflix.client import client_main


def setup_logging():
    """Configure the logging."""
    logging.basicConfig(level=logging.DEBUG)


def main_service():
    """Handles the `mainservice` CLI command."""
    setup_logging()
    logging.info("Main service starting...")
    sys.exit(MainApp().main(sys.argv))


def catalog_service():
    """Handles the `catalogservice` CLI command."""
    setup_logging()
    logging.info("Media catalog service starting...")
    sys.exit(MediaCatalogApp().main(sys.argv))


def streamprovider_service():
    """Handles the `streamingservice` CLI command."""
    print("Streaming service")
    sys.exit(0)


def authentication_service():
    """Handles the `authenticationservice` CLI command."""
    setup_logging()
    logging.info("Authentication service starting...")
    sys.exit(AuthenticatorApp().main(sys.argv))


def client():
    """Handles the IceFlix client CLI command."""
    print("Starting IceFlix client...")
    client_main()
    sys.exit(0)
