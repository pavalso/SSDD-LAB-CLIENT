import os
import shlex
import sys
import logging

import Ice

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix

from time import sleep
from hashlib import sha256
from getpass import getpass
from dataclasses import dataclass
from threading import Thread



MAX_TRIES = 3

WARNING_WAIT = 1
ERROR_WAIT = 2

class _Services:
    _authenticator = 'authenticator'
    _catalog = 'catalog'

    def getAuthenticator():
        return _Services._get_service(_Services._authenticator)

    def getCatalog():
        return _Services._get_service(_Services._catalog)

    def _get_service(service):
        if service == _Services._authenticator:
            main_get = main.getAuthenticator
        elif service == _Services._catalog:
            main_get = main.getCatalog
        else:
            raise RuntimeError('Unknown service')

        logging.info(f'Trying to get {service} service from main server...')

        i = 0
        for i in range(1, MAX_TRIES):
            try:
                return main_get()
            except IceFlix.TemporaryUnavailable:
                logging.warning(f"({i}) Couldn't connect to {service} service, trying again in 5 seconds")
                sleep(5)

        try:
            return main_get()
        except IceFlix.TemporaryUnavailable:
            logging.warning(f"({i+1}) Couldn't connect to {service}")
            raise IceFlix.TemporaryUnavailable()


@dataclass
class Session:
    user: str = None
    passHash: str = None
    token: str = None
    isAnon: bool = False

    def __post_init__(self):
        self.isAnon = self.token is None
        self.user = self.user if not self.isAnon else 'Anonymous'

    def refresh(self):
        try:
            authenticator = _Services.getAuthenticator()
        except IceFlix.TemporaryUnavailable:
            print('Authentication service is unavailable')
            sleep(ERROR_WAIT)
        
        current_session.token = None
        new_token = authenticator.refreshAuthorization(self.user, self.passHash)
        current_session.token = new_token

current_session : Session = Session()
main = None
__communicator = None

__cached_tiles = { }
selected_title : IceFlix.Media = None

def needCreds(func):
    def checkCreds(*args, **kwargs):
        if current_session.isAnon:
            print("This command cannot be executed as an anonymous user\nUse the command 'logout' and switch to an authenticated account.")
            return
        func(*args, **kwargs)
    checkCreds.__doc__ = f'{func.__doc__ }\n\t[Requires an authenticated account to be executed]'
    return checkCreds

def initialize_program(proxy):
    global main, __communicator
    try:
        __communicator = Ice.initialize(sys.argv)
        base = __communicator.stringToProxy(proxy)
        main = IceFlix.MainPrx.checkedCast(base)
        if not main:
            raise RuntimeError("Check the main proxy spelling. The one given couldn't be reached")
    except Ice.ConnectionRefusedException:
        __communicator.destroy()
        raise Ice.ConnectionRefusedException

    def _check_conn():
        while main is not None:
            try:
                main.ice_ping()
                sleep(5)
            except Ice.ConnectionRefusedException:
                print('Lost connection with the server.')
                os._exit(0)

    #def _
    
    thread = Thread(target=_check_conn)
    thread.setDaemon(True)
    thread.start()

def _authenticate():
    global current_session

    current_session = Session()
    print(f'Connecting to the authentication services...')
    try:
        authenticator = _Services.getAuthenticator()
    except IceFlix.TemporaryUnavailable:
        print('Authentication service is unavailable')
        sleep(ERROR_WAIT)
        return
    
    for i in range(3):
        user = input('Username: ')
        password = getpass('Password: ')
        sha256password = sha256(password.encode('utf-8')).hexdigest()
        try:
            token = authenticator.refreshAuthorization(user, sha256password)
            current_session = Session(user, sha256password, token)
            return
        except IceFlix.Unauthorized:
            print('Wrong combination of user/password')
            sleep(WARNING_WAIT)

def _get_titles_name(catalog, name, exact = True):
    tiles = catalog.getTilesByName(name, exact)
    _save_tiles(catalog, tiles)
    _show_cached_media()

def _get_titles_tag(catalog, tags, includeAllTags = True):
    tiles = catalog.getTilesByTags(tags, includeAllTags, current_session.token)
    _save_tiles(catalog, tiles)
    _show_cached_media()

def _save_tiles(catalog, tiles):
    if not tiles:
        return
    __cached_tiles.clear()
    for id in tiles:
        try:
            media = catalog.getTile(id, current_session.token)
        except IceFlix.WrongMediaId:
            continue
        __cached_tiles[id] = media  

def _show_cached_media():
    buff = ''
    for id, media in __cached_tiles.items():
        tags = ', '.join(media.info.tags)
        buff += f'{id}: {media.info.name} | {tags}\n'
    print('No titles' if not buff else buff[:-1])

def login():
    try:
        if input('Authenticate? [Yy/Nn]: ').lower() == 'y':
            _authenticate()
        print(f"\nWelcome {current_session.user}!\n\nUse 'help' for a list of the available commands\n")
    except (KeyboardInterrupt, EOFError):
        shutdown()

def _on_invalid_command(*_):
    print("Command not found, try 'help' for a list of available commands")

def show_logo():
    print(r'''
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
''')

def help(*commands):
    '''Prints this message. 
    Can receive multiple command names to limit the output.
    Usage: help commands*'''
    buff = ''
    for command, func in AVAILABLE_COMMANDS.items():
        if not commands or command in commands:
            buff += '{0: <20}{1}\n\n'.format(command, func.__doc__)
    print('Unknown command' if not buff else buff[:-2])

def logout():
    '''Closes the current session and allows you to change your creedentials.
    Usage: logout'''
    global current_session
    print('')
    current_session = Session()
    login()

def shutdown():
    '''Closes any active session and finish the program.
    Usage: shutdown'''
    print('Goodbye!')
    __communicator.destroy()
    exit(0)

@needCreds
def get_titles(tag = 'name'):
    '''Retrieves titles from the catalog server.
    Usage: get_titles filter["name"/"tag"] -> "name" by default'''
    try:
        catalog = _Services.getCatalog()
        if tag.lower() == 'tag':
            tags_raw = input('Tags list (each tag inside " "): ')
            tags = shlex.split(tags_raw) 
            includeAllTags = input('Must have all the tags? [Yy/Nn]: ').lower() == 'y'
            _get_titles_tag(catalog, tags, includeAllTags)
        else:
            name = input('Title name: ')
            exact = input('Exact match? [Yy/Nn]: ').lower() == 'y'
            _get_titles_name(catalog, name, exact)
    except IceFlix.TemporaryUnavailable:
        print('Catalog service is unavailable')
        return

def select_title():
    '''Selects a title to use.
    First needs to fetch it with the command 'get_titles'.
    Usage: select_title'''
    global selected_title
    if not __cached_tiles:
        print("No media in cache, please get some using the command 'get_titles'")
        return
    _show_cached_media()
    id = input('Title id: ')
    title = __cached_tiles.get(id)
    if not title:
        print('No title with that id')
        return
    selected_title = title
    print(f'Selected {selected_title.info.name}')

def execute_command(command, *args):
    try:
        AVAILABLE_COMMANDS.get(command, _on_invalid_command)(*args)
    except IceFlix.Unauthorized:
        print('Token expired, refreshing the token')
        try:
            current_session.refresh()
        except IceFlix.Unauthorized:
            print("Couldn't refresh the token, your creedentials might have changed")
            logout()
    except TypeError:
        print(f"Wrong spelling, executing 'help {command}':")
        help(command)

AVAILABLE_COMMANDS = {
    'help': help,
    'logout': logout,
    'exit': shutdown,
    'get_titles': get_titles,
    'select_title': select_title
}
