import os
import sys
import logging

import Ice
import cmd2

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix
import parsers

from threading import Thread
from dataclasses import dataclass, field
from getpass import getpass
from hashlib import sha256
from time import sleep


MAX_TRIES = 3

COLOR_SELECTED_TITLE = cmd2.ansi.RgbFg(200,200,200)
COLOR_CONNECTED = cmd2.ansi.RgbFg(150,225,255)
COLOR_DISCONNECTED = cmd2.ansi.RgbFg(200,0,0)

@dataclass
class ActiveConnection:
    terminal : cmd2.Cmd
    communicator : Ice.CommunicatorI = None
    main = None
    proxy : str = None
    
    reachable : bool = False

    def __post_init__(self) -> None:
        Thread(target=self._periodic_conn_check, daemon=True).start()

    def _periodic_conn_check(self):
        last_val = self.reachable
        while True:
            try:
                if self.main:
                    self.main.ice_ping()
                    self.reachable = True
                sleep(5)
            except Ice.ConnectionRefusedException:
                self.reachable = False
            except Ice.CommunicatorDestroyedException:
                return
            if not last_val == self.reachable and self.terminal.terminal_lock.acquire():
                self.terminal.async_update_prompt(self.terminal._generate_prompt())
                self.terminal.terminal_lock.release()
                last_val = self.reachable

    def get_authenticator(self):
        if not self.main:
            self.terminal.perror('No active connection to a main server')
            return None

        for i in range(1, MAX_TRIES):
            try:
                prx = self.main.getAuthenticator()
            except IceFlix.TemporaryUnavailable:
                if not i == MAX_TRIES:
                    logging.warning(
                        "(%i) Couldn't connect to the authentication service, trying again in 5 seconds",
                        i
                    )
                    sleep(5)
            except Ice.ConnectionRefusedException:
                self.terminal.perror('Connection refused')
                return None
            else:
                return prx

        self.terminal.perror('Authentication services unavailable')
        logging.error(
            "Couldn't connect to the authentication service after %i tries",
            MAX_TRIES
        )
        return None

    def get_catalog(self):
        if not self.main:
            self.terminal.perror('No active connection to a main server')
            return None

        try:
            prx = self.main.getCatalog()
        except IceFlix.TemporaryUnavailable:
            self.terminal.perror('Catalog services unavailable')
        except Ice.ConnectionRefusedException:
            self.terminal.perror('Connection refused')
        else:
            return prx

        return None

@dataclass
class PartiaMedia:
    id : str
    name : str = None
    tags : list[str] = None

    media : IceFlix.Media = None

    def fetch(self, conn : ActiveConnection):
        catalog = conn.get_catalog()

        if not catalog:
            return None
        
        session = conn.terminal.session
        if session.is_anon:
            return None

        try:
            self.media = catalog.getTile(self.id, conn.terminal.session.token)
        except:
            pass
        else:
            return self.media
        return None

    def __str__(self) -> str:
        name = f'name: {self.name}' if self.name is not None else None
        tags = 'tags: {0}'.format(','.join(self.tags)) if self.tags is not None else None
        data = ' -> '.join([string for string in [name, tags] if string is not None])
        return '{0}. {1}'.format(self.id, 'Nothing to show' if not data else data)

@dataclass
class Session:
    '''Stores the current session data'''
    user: str = None
    pass_hash: str = None
    token: str = None
    is_anon: bool = False
    selected_title : PartiaMedia = None
    cached_titles : dict[str, PartiaMedia] = field(default_factory=dict[str, PartiaMedia])

    def __post_init__(self):
        self.is_anon = self.token is None
        self.display_name = self.user if self.user else 'User'

class Commands:

    @staticmethod
    def stablish_connection_main(conn : ActiveConnection, proxy):
        # TODO: __doc__ and error logging
        
        communicator = Ice.initialize(sys.argv)
        base = communicator.stringToProxy(proxy)
        
        try:
            main = IceFlix.MainPrx.checkedCast(base)
        except Ice.ConnectionLostException:
            conn.terminal.perror('Connection lost')
        except Ice.ConnectionTimeoutException:
            conn.terminal.perror('Connection timeout') 
        except Ice.ObjectNotExistException as error:
            conn.terminal.perror(f'{error.id.name} is an invalid object')
        except Ice.ConnectionRefusedException:
            conn.terminal.perror('Connection refused')
        except Ice.NoEndpointException:
            conn.terminal.perror('Proxy needs an endpoint')
        else:
            if not main:
                conn.terminal.perror("Given proxy is invalid")
                communicator.destroy()
                return None

            if conn.communicator is not None and not conn.communicator.isShutdown():
                conn.communicator.destroy()

            conn.communicator = communicator
            conn.main = main
            conn.proxy = proxy
            conn.reachable = True
            return conn
        communicator.destroy()
        return None

    @staticmethod
    def login(conn : ActiveConnection):
        auth = conn.get_authenticator()

        if auth is None:
            return None

        username = conn.terminal.read_input('Username: ')
        password = getpass('Password: ')
        password_hash = sha256(password.encode('utf-8')).hexdigest()

        try:
            token = auth.refreshAuthorization(username, password_hash)
        except IceFlix.Unauthorized:
            conn.terminal.perror('Wrong username/password combination')
        except Ice.ConnectionRefusedException as conn_refused:
            conn.terminal.perror('Lost connection to the authentication services')
            conn.terminal.pexcept(conn_refused)
        else:
            conn.terminal.session = Session(username, password_hash, token)
            return conn.terminal.session
        return None

    @staticmethod
    def get_catalog_name(conn : ActiveConnection, name : str, exact : bool):
        catalog = conn.get_catalog()

        if catalog is None:
            return

        try:
            titles = catalog.getTilesByName(name, exact)
        except Ice.ConnectionRefusedException as conn_refused:
            conn.terminal.perror('Lost connection to the catalog service')
            conn.terminal.pexcept(conn_refused)
        else:
            if not titles:
                if exact:
                    conn.terminal.perror(f'None of the media is titled: {name}')
                else:
                    conn.terminal.perror(f'None of the media contains: {name}')
                return
            pmedia = PartiaMedia(titles[0], name=name)
            buffer = {pmedia.id: pmedia}
            Commands.save_pmedia(conn, buffer)
            Commands.show_titles(conn, buffer)
        return

    @staticmethod
    def get_catalog_tags(conn : ActiveConnection, tags : list[str], include_all : bool):
        catalog = conn.get_catalog()

        if catalog is None:
            return

        try:
            titles = catalog.getTilesByTags(tags, include_all, conn.terminal.session.token)
        except Ice.ConnectionRefusedException as conn_refused:
            conn.terminal.perror('Lost connection to the catalog service')
            conn.terminal.pexcept(conn_refused)
        else:
            if not titles:
                if include_all:
                    conn.terminal.perror('No media that have the tags: {0}'.format(', '.join(tags)))
                else:
                    conn.terminal.perror('No media that have any of this tags: {0}'.format(', '.join(tags)))
                return
            buffer = {id: PartiaMedia(id, tags=tags) for id in titles}
            Commands.save_pmedia(conn, buffer)
            Commands.show_titles(conn, buffer)
        return

    @staticmethod
    def use_title(conn : ActiveConnection, id : str):
        if id not in conn.terminal.session.cached_titles:
            return None
        pmedia = conn.terminal.session.cached_titles[id]
        conn.terminal.session.selected_title = pmedia
        conn.terminal.poutput(f'Selected: {pmedia}')

    def save_pmedia(conn : ActiveConnection, media : dict[str, PartiaMedia]):
        union = set(conn.terminal.session.cached_titles).intersection(media)
        for id in union:
            updated = media[id]
            cached = conn.terminal.session.cached_titles[id]
            updated.name = cached.name if updated.name is None else updated.name
            updated.tags = cached.tags if updated.tags is None else updated.tags
            
        conn.terminal.session.cached_titles.update(media)

    @staticmethod
    def show_titles(conn : ActiveConnection, titles : dict[str, PartiaMedia]):
        buffer = ''
        for pmedia in titles.values():
            buffer += str(pmedia)
        if not buffer:
            conn.terminal.perror('No media to show')
            return
        conn.terminal.poutput(buffer)

    def add_tags(conn : ActiveConnection, tags : list[str]):
        catalog = conn.get_catalog()
        if not catalog:
            return
        title = conn.terminal.session.selected_title
        if not title.tags:
            title.tags = []
        title.tags.extend(tags)
        title.tags = list(set(title.tags))
        catalog.addTags(title.id, tags, conn.terminal.session.token)

    def remove_tags(conn : ActiveConnection, tags : list[str]):
        title = conn.terminal.session.selected_title
        if not title.tags:
            return
        catalog = conn.get_catalog()
        if not catalog:
            return
        tags = list(set(title.tags).difference(tags))
        title.tags = None if not tags else tags
        catalog.removeTags(title.id, tags, conn.terminal.session.token)

class cli_handler(cmd2.Cmd):
    '''Handles user input via an interactive command line'''

    session : Session
    active_conn : ActiveConnection

    def __init__(self) -> None:
        self.active_conn = ActiveConnection(self)
        self.session = Session()
        super().__init__()

        self.debug = True

        Commands.stablish_connection_main(self.active_conn, 'MainAdapter -t -e 1.1:tcp -h 192.168.1.204 -p 9999 -t 60000')#self.read_input('Connection proxy: '))
        
        self.prompt = self._generate_prompt()

    @staticmethod
    def need_creds(func):
        '''If the user is anon, don't run the command and inform the user'''
        def check_creds(self, *args, **kwargs):
            if self.session.is_anon:
                self.perror(
                    '''This command is only available for authenticated users
use the command 'logout' and authenticate in order to use it'''
                )
                return
            func(self, *args, **kwargs)
        return check_creds

    def get_user_consent(self, prompt) -> bool:
        return self.read_input(f'{prompt} [Yy/Nn]: ').lower() == "y"

    @cmd2.with_argparser(parsers.reconnect_parser)
    def do_reconnect(self, args):
        prx = self.active_conn.proxy if args.proxy is None else args.proxy
        Commands.stablish_connection_main(self.active_conn, prx)

    def do_logout(self, line):
        self.session = Session()
        try:
            if self.get_user_consent('Wanna log in?'):
                Commands.login(self.active_conn)
            return
        except (KeyboardInterrupt, EOFError):
            self.poutput('')
            return True

    @cmd2.with_argparser(parsers.cat_base)
    def do_catalog(self, args):
        func = getattr(args, 'func', None)
        if not func:
            return self.do_help('catalog')
        func(self, args)

    def get_catalog(self, args):
        func = getattr(args, 'search_func', None)
        if not func:
            return self.do_help('catalog get')
        func(self, args)

    def use_title(self, args):
        Commands.use_title(self.active_conn, args.id)

    def search_name(self, args):
        Commands.get_catalog_name(self.active_conn, args.name, args.exact)

    @need_creds
    def search_tags(self, args):
        Commands.get_catalog_tags(self.active_conn, args.tags, args.include)

    def show_catalog(self, args):
        Commands.show_titles(self.active_conn, self.session.cached_titles)

    parsers.cat_get_base.set_defaults(func=get_catalog)
    parsers.cat_show.set_defaults(func=show_catalog)

    parsers.cat_use.set_defaults(func=use_title)
    parsers.cat_name.set_defaults(search_func=search_name)
    parsers.cat_tags.set_defaults(search_func=search_tags)

    @cmd2.with_argparser(parsers.selected_base)
    @need_creds
    def do_selected(self, args):
        if not self.session.selected_title:
            self.perror("First you need to select a title using 'catalog use id'")
            return
        if not args.tags:
            return
        try:
            if args.add and args.remove:
                self.perror("Only one operation can be specify, remove '--add' or '--remove'")
                return
            if args.add:
                Commands.add_tags(self.active_conn, args.tags)
            elif args.remove:
                Commands.remove_tags(self.active_conn, args.tags)
            else:
                self.perror("You need to specify '--add' or '--remove' first")
        except IceFlix.Unauthorized:
            self.perror("Your session has expired")
        except IceFlix.WrongMediaId as error_media:
            self.perror('The selected media has been removed from the catalog server')
            self.session.cached_titles.pop(self.session.selected_title.id)
            self.session.selected_title = None

    def _generate_prompt(self):
        media = '-#'
        title = self.session.selected_title
        if title is not None:
            media = f'{title.id}#' if title.name is None else f'{title.id}-{title.name}#'
        media = cmd2.ansi.style(media, fg=COLOR_SELECTED_TITLE)
        raw_text = f'{self.session.display_name}:{media} '
        color = COLOR_CONNECTED if self.active_conn.reachable else COLOR_DISCONNECTED 
        return cmd2.ansi.style(raw_text, fg=color)

    def postcmd(self, stop, line):
        self.prompt = self._generate_prompt()
        return stop

    def perror(self, msg: str = '', *, end: str = '\n', apply_style: bool = True) -> None:
        return super().perror(msg, end=end, apply_style=apply_style)

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
