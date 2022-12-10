"""Submodule containing the CLI command handlers."""

import logging
import sys

from iceflix.client import client_main


def setup_logging():
    """Configure the logging."""
    logging.basicConfig(level=logging.DEBUG)

def client():
    """Handles the IceFlix client CLI command."""
    print("Starting IceFlix client...")
    client_main()
    sys.exit(0)
