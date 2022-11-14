"""
    Contains all the calleble commands that the user can use while in the app
"""

# pylint: disable=import-error
# pylint: disable=wrong-import-position

# If not disable, pylint will raise a warning on Ice exceptions.
# pylint: disable=no-member

from threading import Thread
from dataclasses import dataclass
from getpass import getpass
from hashlib import sha256
from time import sleep
import os
import shlex
import sys
import logging

import Ice

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix


MAX_TRIES = 3

WARNING_WAIT = 1
ERROR_WAIT = 2


class _Services:
    _authenticator = "authenticator"
    _catalog = "catalog"

    @staticmethod
    def get_authenticator():
        return _Services._get_service(_Services._authenticator)

    @staticmethod
    def get_catalog():
        return _Services._get_service(_Services._catalog)

    @staticmethod
    def _get_service(service):
        if service == _Services._authenticator:
            main_get = main.getAuthenticator
        elif service == _Services._catalog:
            main_get = main.getCatalog
        else:
            raise RuntimeError("Unknown service")

        logging.info(f"Trying to get {service} service from main server...")

        i = 0
        for i in range(1, MAX_TRIES):
            try:
                return main_get()
            except IceFlix.TemporaryUnavailable:
                logging.warning(
                    f"({i}) Couldn't connect to {service} service, \
                    trying again in 5 seconds"
                )
                sleep(5)

        try:
            return main_get()
        except IceFlix.TemporaryUnavailable:
            logging.warning(f"({i+1}) Couldn't connect to {service}")
            raise IceFlix.TemporaryUnavailable()


@dataclass
class Session:
    '''Stores the current session data'''
    user: str = None
    pass_hash: str = None
    token: str = None
    is_anon: bool = False

    def __post_init__(self):
        self.is_anon = self.token is None
        self.user = self.user if not self.is_anon else "Anonymous"

    def refresh(self):
        try:
            authenticator = _Services.get_authenticator()
        except IceFlix.TemporaryUnavailable:
            print("Authentication service is unavailable")
            sleep(ERROR_WAIT)

        current_session.token = None
        new_token = authenticator.refreshAuthorization(
            self.user, self.pass_hash)
        current_session.token = new_token


current_session: Session = Session()
main = None
__communicator = None

__cached_tiles = {}
selected_title: IceFlix.Media = None


def need_creds(func):
    def check_creds(*args, **kwargs):
        if current_session.is_anon:
            print(
                "This command cannot be executed as an anonymous user\n \
                Use the command 'logout' and switch to an authenticated account."
            )
            return
        func(*args, **kwargs)

    check_creds.__doc__ = (
        f"{func.__doc__ }\n\t[Requires an authenticated account to be executed]"
    )
    return check_creds


def initialize_program(proxy):
    '''Starts the connection with the main server and sends a ping each 5 seconds to see if
    the server stills alive'''
    global main, __communicator
    __communicator = Ice.initialize(sys.argv)
    base = __communicator.stringToProxy(proxy)
    main = IceFlix.MainPrx.checkedCast(base)
    if not main:
        raise RuntimeError(
            "Check the main proxy spelling. The one given couldn't be reached"
        )

    def _check_conn():
        while main is not None:
            try:
                main.ice_ping()
                sleep(5)
            except Ice.ConnectionRefusedException:
                print("Lost connection with the server.")
                # Must use os._exit as this function is called in a thread that
                # needs to end the whole program execution when no connection with main
                # pylint: disable=protected-access
                os._exit(0)

    Thread(target=_check_conn, daemon=True).start()


def _authenticate():
    global current_session

    current_session = Session()
    print("Connecting to the authentication services...")
    try:
        authenticator = _Services.get_authenticator()
    except IceFlix.TemporaryUnavailable:
        print("Authentication service is unavailable")
        sleep(ERROR_WAIT)
        return

    for _ in range(3):
        user = input("Username: ")
        password = getpass("Password: ")
        sha256password = sha256(password.encode("utf-8")).hexdigest()
        try:
            token = authenticator.refreshAuthorization(user, sha256password)
            current_session = Session(user, sha256password, token)
            return
        except IceFlix.Unauthorized:
            print("Wrong combination of user/password")
            sleep(WARNING_WAIT)


def _get_titles_name(catalog, name, exact=True):
    tiles = catalog.getTilesByName(name, exact)
    _save_tiles(catalog, tiles)
    _show_cached_media()


def _get_titles_tag(catalog, tags, include_all_tags=True):
    tiles = catalog.getTilesByTags(tags, include_all_tags, current_session.token)
    _save_tiles(catalog, tiles)
    _show_cached_media()


def _save_tiles(catalog, media_ids):
    if not media_ids:
        return
    __cached_tiles.clear()
    for media_id in media_ids:
        try:
            media = catalog.getTile(media_id, current_session.token)
        except IceFlix.WrongMediaId:
            continue
        __cached_tiles[media_id] = media


def _show_cached_media():
    buff = ""
    for media_id, media in __cached_tiles.items():
        tags = ", ".join(media.info.tags)
        buff += f"{media_id}: {media.info.name} | {tags}\n"
    print("No titles" if not buff else buff[:-1])


def login():
    '''Allows to change the session to an anonimous or an authenticated one'''
    try:
        if input("Authenticate? [Yy/Nn]: ").lower() == "y":
            _authenticate()
        print(
            f"\nWelcome {current_session.user}!\
            \n\nUse 'help' for a list of the available commands\n"
        )
    except (KeyboardInterrupt, EOFError):
        shutdown()


def _on_invalid_command(*_):
    print("Command not found, try 'command_help' for a list of available commands")


def show_logo():
    '''Prints in screen the app logo'''
    print(
        r"""
 ██▓ ▄████▄  ▓█████   █████▒██▓     ██▓▒██   ██▒
▓██▒▒██▀ ▀█  ▓█   ▀ ▓██   ▒▓██▒    ▓██▒▒▒ █ █ ▒░
▒██▒▒▓█    ▄ ▒███   ▒████ ░▒██░    ▒██▒░░  █   ░
░██░▒▓▓▄ ▄██▒▒▓█  ▄ ░▓█▒  ░▒██░    ░██░ ░ █ █ ▒
░██░▒ ▓███▀ ░░▒████▒░▒█░   ░██████▒░██░▒██▒ ▒██▒
░▓  ░ ░▒ ▒  ░░░ ▒░ ░ ▒ ░   ░ ▒░▓  ░░▓  ▒▒ ░ ░▓ ░
 ▒ ░  ░  ▒    ░ ░  ░ ░     ░ ░ ▒  ░ ▒ ░░░   ░▒ ░
 ▒ ░░           ░    ░ ░     ░ ░    ▒ ░ ░    ░
 ░  ░ ░         ░  ░           ░  ░ ░   ░    ░
    ░
"""
    )


def command_help(*commands):
    """Prints this message.
    Can receive multiple command names to limit the output.
    Usage: command_help commands*"""
    buff = ""
    for command, func in AVAILABLE_COMMANDS.items():
        if not commands or command in commands:
            buff += f"{command: <20}{func.__doc__}\n\n"
    print("Unknown command" if not buff else buff[:-2])


def logout():
    """Closes the current session and allows you to change your creedentials.
    Usage: logout"""
    global current_session
    print("")
    current_session = Session()
    login()


def shutdown():
    """Closes any active session and finish the program.
    Usage: shutdown"""
    print("Goodbye!")
    __communicator.destroy()
    sys.exit(0)


@need_creds
def get_titles(tag="name"):
    """Retrieves titles from the catalog server.
    Usage: get_titles filter["name"/"tag"] -> "name" by default"""
    try:
        catalog = _Services.get_catalog()
        if tag.lower() == "tag":
            tags_raw = input('Tags list (each tag inside " "): ')
            tags = shlex.split(tags_raw)
            include_all_tags = input(
                "Must have all the tags? [Yy/Nn]: ").lower() == "y"
            _get_titles_tag(catalog, tags, include_all_tags)
        else:
            name = input("Title name: ")
            exact = input("Exact match? [Yy/Nn]: ").lower() == "y"
            _get_titles_name(catalog, name, exact)
    except IceFlix.TemporaryUnavailable:
        print("Catalog service is unavailable")
        return


def select_title():
    """Selects a title to use.
    First needs to fetch it with the command 'get_titles'.
    Usage: select_title"""
    global selected_title
    if not __cached_tiles:
        print("No media in cache, please get some using the command 'get_titles'")
        return
    _show_cached_media()
    tittle_id = input("Title id: ")
    title = __cached_tiles.get(tittle_id)
    if not title:
        print("No title with that id")
        return
    selected_title = title
    print(f"Selected {selected_title.info.name}")


def execute_command(command, *args):
    try:
        AVAILABLE_COMMANDS.get(command, _on_invalid_command)(*args)
    except IceFlix.Unauthorized:
        print("Token expired, refreshing the token")
        try:
            current_session.refresh()
        except IceFlix.Unauthorized:
            print("Couldn't refresh the token, your creedentials might have changed")
            logout()
    except TypeError:
        print(f"Wrong spelling, executing 'help {command}':")
        command_help(command)


AVAILABLE_COMMANDS = {
    "help": command_help,
    "logout": logout,
    "exit": shutdown,
    "get_titles": get_titles,
    "select_title": select_title,
}
