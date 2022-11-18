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
from time import sleep, perf_counter_ns


MAX_TRIES = 3

COLOR_SELECTED_TITLE = cmd2.ansi.RgbFg(200,200,200)

COLOR_CONNECTED = cmd2.ansi.RgbFg(0,225,255)
COLOR_DISCONNECTED = cmd2.ansi.RgbFg(200,0,0)

COLOR_ADMIN = cmd2.ansi.RgbFg(225,0,255)

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
            except Ice.ConnectTimeoutException:
                self.reachable = False
            except Ice.CommunicatorDestroyedException:
                return
            if not last_val == self.reachable and self.terminal.terminal_lock.acquire(blocking=False):
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
            except Ice.ConnectTimeoutException:
                self.terminal.perror('Connection timeout')
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
        except Ice.ConnectTimeoutException:
            self.terminal.perror('Connection timedout')
            return None
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
            media = catalog.getTile(self.id, conn.terminal.session.token)
        except IceFlix.TemporaryUnavailable:
            conn.terminal.perror("Can't fetch media rigth now, try again later")
        except IceFlix.Unauthorized:
            conn.terminal.perror("Your session has expired")
        except IceFlix.WrongMediaId:
            conn.terminal.perror('This media seems to not exist on the catalog server')
        else:
            if media.info:
                self.name = media.info.name
                self.tags = media.info.tags
            self.media = media
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
    admin_pass: str = None
    token: str = None
    is_anon: bool = False
    is_admin: bool = False
    selected_title : PartiaMedia = None
    cached_titles : dict[str, PartiaMedia] = field(default_factory=dict[str, PartiaMedia])

    __cached_token : str = None

    def __post_init__(self):
        self.is_anon = self.token is None
        self.display_name = self.user if self.user else 'User'

    def make_admin(self, admin_password : str):
        self.__cached_token = self.token
        self.admin_pass = admin_password
        self.token = admin_password
        self.is_admin = True

    def make_user(self):
        self.token = self.__cached_token
        self.__cached_token = None
        self.admin_pass = None
        self.is_admin = False

    def refresh(self, conn : ActiveConnection):
        auth = conn.get_authenticator()

        if not auth:
            return None

        try:
            token = auth.refreshAuthorization(self.user, self.pass_hash)
        except Ice.ConnectionRefusedException as conn_refused:
            conn.terminal.perror('Lost connection to the authentication services')
            conn.terminal.pexcept(conn_refused)
        else:
            self.token = token
            self.is_anon = self.token is None
            return self
        return None 

class Commands:

    @staticmethod
    def stablish_connection_main(conn : ActiveConnection, proxy):
        # TODO: __doc__ and error logging
        
        communicator = Ice.initialize(sys.argv)
        base = communicator.stringToProxy(proxy)

        if conn.proxy is None:
            conn.proxy = proxy
        
        try:
            main = IceFlix.MainPrx.checkedCast(base)
        except Ice.ConnectionLostException:
            conn.terminal.perror('Connection lost')
        except Ice.ConnectTimeoutException:
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
            conn.terminal.prompt = conn.terminal._generate_prompt()
            return conn
        communicator.destroy()
        return None

    @staticmethod
    def login(conn : ActiveConnection):
        username = conn.terminal.read_input('Username: ')
        password = getpass('Password: ')
        password_hash = sha256(password.encode('utf-8')).hexdigest()

        try:
            conn.terminal.session = Session(username, password_hash)
            conn.terminal.session.refresh(conn)
        except IceFlix.Unauthorized:
            conn.terminal.perror('Wrong username/password combination')

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
            conn.terminal.perror('No connection with the catalog services')
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
            conn.terminal.perror('No connection with the catalog services')
            return
        tags = list(set(title.tags).difference(tags))
        title.tags = None if not tags else tags
        catalog.removeTags(title.id, tags, conn.terminal.session.token)

    def download(conn : ActiveConnection):
        title = conn.terminal.session.selected_title
        if not title:
            conn.terminal.perror('No selected title')
            return

        media = title.fetch(conn)

        if not media:
            return

        if not media.provider:
            conn.terminal.perror("The title selected couldn't be downloaded, no provider associated")
            return

        session = conn.terminal.session
        try:
            handler = title.media.provider.openFile(title.id, session.token)
        except IceFlix.Unauthorized:
            conn.terminal.perror('Your session has expired')
        except IceFlix.WrongMediaId:
            conn.terminal.perror('The selected media seems to not exist on the catalog server')
        else:
            with conn.terminal.terminal_lock:
                conn.terminal.poutput(f"Starting download...")
                time_initial = perf_counter_ns()
                with open(title.name, 'wb') as file:
                    try:
                        while True:
                            try:
                                raw = handler.receive(2048, session.token)
                                if not raw:
                                    break
                                file.write(raw)
                            except IceFlix.Unauthorized:
                                session.refresh(conn)
                    except IceFlix.Unauthorized:
                        conn.terminal.perror('Your credentials changed. The download has been aborted')
                    else:
                        time_end = perf_counter_ns()
                        final_time = time_end - time_initial
                        conn.terminal.poutput(f"Finished downloading: '{title.name}' in {final_time / 10**9:.2f} seconds")
                        handler.close(session.token)
                        return
                    os.remove(title.name)
        return

    def admin(conn : ActiveConnection):
        admin_pass = getpass('Admin password: ')
        admin_sha256_pass = sha256(admin_pass.encode('utf-8')).hexdigest()
        auth = conn.get_authenticator()
        if not auth:
            return
        if not auth.isAdmin(admin_sha256_pass):
            conn.terminal.perror('Wrong password')
            return
        conn.terminal.session.make_admin(admin_sha256_pass)
        return conn.terminal.session

    def add_user(conn : ActiveConnection, user : str, password : str):
        auth = conn.get_authenticator()

        if not auth:
            return

        password_hash = sha256(password.encode('utf-8')).hexdigest()
        try:
            auth.addUser(user, password_hash, conn.terminal.session.admin_pass)
        except IceFlix.Unauthorized:
            conn.terminal.perror('Invalid admin creedentials')
        except IceFlix.TemporaryUnavailable:
            conn.terminal.perror('Authentication services unavailable')
        else:
            conn.terminal.poutput(f'Added user {user}')

    def remove_user(conn : ActiveConnection, user : str):
        auth = conn.get_authenticator()

        if not auth:
            return

        try:
            auth.removeUser(user, conn.terminal.session.admin_pass)
        except IceFlix.Unauthorized:
            conn.terminal.perror('Invalid admin creedentials')
        except IceFlix.TemporaryUnavailable:
            conn.terminal.perror('Authentication services unavailable')
        else:
            conn.terminal.poutput(f'Removed user {user}')

class cli_handler(cmd2.Cmd):
    '''Handles user input via an interactive command line'''

    session : Session
    active_conn : ActiveConnection

    def __init__(self) -> None:
        self.active_conn = ActiveConnection(self)
        self.session = Session()
        super().__init__()

        self.debug = True

        self.prompt = self._generate_prompt()

    def connect(self, proxy):
        Commands.stablish_connection_main(self.active_conn, proxy)

    @staticmethod
    def need_creds(func):
        '''If the user is anon, don't run the command and inform the user'''
        def check_creds(self, *args, **kwargs):
            if self.session.is_anon and not self.session.is_admin:
                self.perror(
                    '''This command is only available for authenticated users
use the command 'logout' and authenticate in order to use it'''
                )
                return
            func(self, *args, **kwargs)
        check_creds.__name__ = func.__name__
        return check_creds

    @staticmethod
    def need_admin(func):
        '''If the user is anon, don't run the command and inform the user'''
        def check_admin(self, *args, **kwargs):
            if not self.session.is_admin:
                self.perror('Insufficient permissions')
                return
            func(self, *args, **kwargs)
        check_admin.__name__ = func.__name__
        return check_admin

    def get_user_consent(self, prompt) -> bool:
        return self.read_input(f'{prompt} [Yy/Nn]: ').lower() == "y"

    @cmd2.with_argparser(parsers.reconnect_parser)
    def do_reconnect(self, args):
        prx = self.active_conn.proxy if args.proxy is None else args.proxy
        Commands.stablish_connection_main(self.active_conn, prx)

    def do_logout(self, args):
        self.session = Session()
        try:
            with self.terminal_lock:
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

    @cmd2.with_argparser(parsers.tags_parser)
    @need_creds
    def do_tags(self, args):
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
        except IceFlix.WrongMediaId:
            self.perror('The selected media seems to not exist on the catalog server')

    @cmd2.with_argparser(parsers.download_parser)
    @need_creds
    def do_download(self, args):
        Commands.download(self.active_conn)

    @cmd2.with_argparser(parsers.admin_parser)
    def do_admin(self, args):
        if not self.session.is_admin:
            if not Commands.admin(self.active_conn):
                return
            called_as_admin = False
        else:
            called_as_admin = True
        if args.command:
            func = self.cmd_func(args.command)
            if not func:
                return
            try:
                func(' '.join(args.arguments))
            finally:
                if not called_as_admin:
                    self.session.is_admin = False
                    self.session.admin_pass = None

    def do_exit(self, args):
        if not self.session.is_admin:
            return True
        self.session.make_user()

    @cmd2.with_argparser(parsers.users_parser_base)
    @need_admin
    def do_users(self, args):
        func = getattr(args, 'func', None)
        if not func:
            return self.do_help('catalog')
        func(self, args)

    def users_add(self, args):
        Commands.add_user(self.active_conn, args.user, args.password)

    def users_remove(self, args):
        Commands.remove_user(self.active_conn, args.user)

    parsers.users_add.set_defaults(func=users_add)
    parsers.users_remove.set_defaults(func=users_remove)

    def shutdown(self):
        if self.active_conn and self.active_conn.communicator is not None:
            self.active_conn.communicator.destroy()

    def _generate_prompt(self):
        media = '-#'
        title = self.session.selected_title
        if title is not None:
            media = f'{title.id}#' if title.name is None else f'{title.id}-{title.name}#'
        media = cmd2.ansi.style(media, fg=COLOR_SELECTED_TITLE)
        raw_text = f'{self.session.display_name}:{media} '
        if not self.session.is_admin:
            color = COLOR_CONNECTED if self.active_conn.reachable else COLOR_DISCONNECTED
            admin_indicator = ''
        else:
            color = COLOR_ADMIN if self.active_conn.reachable else COLOR_DISCONNECTED
            admin_indicator = '★'
        return cmd2.ansi.style(f'{admin_indicator}{raw_text}', fg=color)

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
