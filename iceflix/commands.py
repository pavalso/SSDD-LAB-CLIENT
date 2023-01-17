'''
    Cmd handling
'''

# pylint: disable=import-error, wrong-import-position, no-member

from enum import Enum
from threading import Event, current_thread, main_thread, Thread

from dataclasses import dataclass, field
from getpass import getpass
from hashlib import sha256
from time import sleep, perf_counter_ns

try:
    from file_uploader import FileUploaderApp
    from connection import ConnectionCheckerApp
    import event_listener
    import parsers
except ImportError:
    from iceflix.file_uploader import FileUploaderApp
    from iceflix.connection import ConnectionCheckerApp
    from iceflix import event_listener
    from iceflix import parsers

import os
import sys
import logging

import Ice
import cmd2

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix


MAX_TRIES = 3

COLOR_SELECTED_TITLE = cmd2.ansi.RgbFg(200,200,200)

class COLORS(Enum):
    '''
        Colors for each type of user and connection state
    '''
    ANON = cmd2.ansi.RgbFg(255,255,255)
    USER = cmd2.ansi.RgbFg(0,100,255)
    ADMIN = cmd2.ansi.RgbFg(255,0,0)
    DISCONNECTED = cmd2.ansi.RgbFg(0,0,0)

class NoMainError(Exception):
    '''
        If no connection with main server this is raised
    '''
    def __init__(self) -> None:
        super().__init__('No active connection to the main server')

@dataclass
class ActiveConnection:
    '''
        Represents a connection (Connected or not) with a main server
    '''
    terminal : cmd2.Cmd
    communicator : Ice.CommunicatorI = None
    _main = None
    proxy : str = None

    reachable = Event()
    remote : str = '-'
    _conn_check: ConnectionCheckerApp = None

    @property
    def main(self):
        '''
            Returns a main server proxy
        '''
        self.main = self._conn_check.servant.get_main()
        logging.debug('Selected main %s', self._main)
        return self._main

    @main.setter
    def main(self, new):
        if self._main == new:
            return None
        self._main = new
        if new is not None:
            self.reachable.set()
        else:
            self.reachable.clear()
        if current_thread() == main_thread():
            return self.__set_prompt()
        return self.__async_set_prompt()

    def _check_conn(self):
        while not sleep(10):
            main = self._conn_check.servant.get_main()
            self.main = main

    def __set_prompt(self):
        self.terminal.prompt = self.terminal.get_prompt()

    def __async_set_prompt(self):
        if self.terminal.terminal_lock.acquire(blocking=False):
            self.terminal.async_update_prompt(self.terminal.get_prompt())
            self.terminal.terminal_lock.release()

    def __post_init__(self) -> None:
        self.communicator = Ice.initialize(sys.argv)
        self._conn_check = ConnectionCheckerApp(self.communicator, self)
        self._conn_check.main()
        Thread(target=self._check_conn, daemon=True).start()

    def connect_topic_manager(self, topic_proxy: str) -> None:
        '''
            Connects to topic manager at topic_proxy
        '''
        self.main = None
        self._conn_check.subscribe_to_proxy(topic_proxy)
        self.remote = self._conn_check._topic.ice_getConnection().getEndpoint().getInfo().host

    def disconnect_topic_manager(self) -> None:
        '''
            Disconnects from the connected topic manager
        '''
        self.remote = '-'
        self._conn_check.disconnect()

    @staticmethod
    def needs_main(func):
        '''
            Only runs the command if the main server is reachable
        '''
        def wrapper(self, *args, **kwargs):
            if not self.reachable.is_set() or not self.main:
                raise NoMainError
            return func(self, *args, **kwargs)
        return wrapper

    @needs_main
    def get_authenticator(self):
        '''
            Retrieves an authenticator from the main server
        '''
        logging.info('Obtaining an authenticator from main server...')
        authenticator = self.main.getAuthenticator()
        logging.debug('Got authenticator proxy %s', authenticator)
        return authenticator

    @needs_main
    def get_catalog(self):
        '''
            Retrieves a catalog from the main server
        '''
        logging.info('Obtaining a catalog from main server...')
        catalog = self.main.getCatalog()
        logging.debug('Got catalog proxy %s', catalog)
        return catalog

    @needs_main
    def get_file_service(self):
        '''
            Retrieves a file service from the main server
        '''
        logging.info('Obtaining a file service from main server...')
        file_service = self.main.getFileService()
        logging.debug('Got file service proxy %s', file_service)
        return file_service

@dataclass
class PartiaMedia:
    '''
        Represents a media if any of its atributes is known
    '''
    id : str
    name : str = None
    tags : list[str] = None

    media : IceFlix.Media = None

    def fetch(self, conn : ActiveConnection):
        '''
            Gets this media from the catalog server, updating all its information
        '''
        catalog = conn.get_catalog()

        session = conn.terminal.session
        if session.is_anon:
            logging.warning("Can't fetch media if the user is anon")
            return None

        logging.info('Fetching tile %s from the catalog', self.id)
        media = catalog.getTile(self.id, session.token)
        if media.info:
            self.name = media.info.name
            self.tags = media.info.tags
        self.media = media
        logging.debug('Got tile: %s', self)
        return self.media

    def __str__(self) -> str:
        name = f'name: {self.name}' if self.name is not None else None
        tags_list = ','.join(self.tags) if self.tags is not None else None
        tags = f'tags: {tags_list}' if self.tags is not None else None
        data = ' -> '.join([string for string in [name, tags] if string is not None])
        media_data = 'A new media' if not data else data
        return f'{self.id}. {media_data}'

@dataclass
class Session:
    '''
        Stores the current session data
    '''
    user: str = None
    pass_hash: str = None
    admin_pass: str = None
    token: str = None
    is_anon: bool = False
    is_admin: bool = False
    selected_title : PartiaMedia = None
    cached_titles : dict[str, PartiaMedia] = field(default_factory=dict[str, PartiaMedia])

    def __post_init__(self):
        self.is_anon = self.token is None
        self.display_name = self.user if self.user else 'User'

    def make_admin(self, admin_password : str):
        '''
            The user becomes an admin
        '''
        self.admin_pass = admin_password
        self.is_admin = True
        logging.info('%s is now an admin', self.user)
        logging.debug('Using admin token %s', self.admin_pass)

    def make_user(self):
        '''
            The user becomes an user
        '''
        self.admin_pass = None
        self.is_admin = False
        logging.info('%s is now an user', self.user)

    def refresh(self, conn : ActiveConnection):
        '''
            Tries to obtain a new token from the authentication services
        '''
        auth = conn.get_authenticator()
        logging.info('Trying to get a token from the authentication services...')
        token = auth.refreshAuthorization(self.user, self.pass_hash)
        self.token = token
        self.is_anon = self.token is None
        logging.debug("This session is using token: '%s'",
            self.token if not self.is_anon else 'No token')
        return self

class Commands:
    '''
        Command logic
    '''

    @staticmethod
    def stablish_connection_main(conn : ActiveConnection, proxy):
        '''
            Tries to reach a main proxy, if it reaches stablish the connection
        '''
        if not proxy:
            return conn.terminal.perror("Proxy can't be empty")

        try:
            conn.connect_topic_manager(proxy)
            if not conn.reachable.wait(timeout=12):
                return conn.terminal.perror('No main service available')
            conn.proxy = proxy
            conn.terminal.poutput('Connection stablished')
            return conn
        except Ice.ObjectNotExistException as error:
            conn.terminal.perror(f'{error.id.name} is an invalid object')
        except Ice.NoEndpointException:
            conn.terminal.perror('Proxy needs an endpoint')
        except (Ice.ProxyParseException, Ice.EndpointParseException) as parse_exception:
            conn.terminal.perror(parse_exception.str)
        return None

    @staticmethod
    @ActiveConnection.needs_main
    def login(conn : ActiveConnection):
        '''
            Connects to the authentication services and authenticate the user
        '''
        retries = conn.communicator.getProperties().getPropertyAsIntWithDefault('LoginRetries', MAX_TRIES)
        retries = max(1, retries)
        username = conn.terminal.read_input('Username: ')
        password = getpass('Password: ')
        password_hash = sha256(password.encode('utf-8')).hexdigest()
        session = Session(username, password_hash)
        try:
            for i in range(1, retries + 1):
                try:
                    session.refresh(conn)
                    conn.terminal.session = session
                    return
                except IceFlix.TemporaryUnavailable as temporary_error:
                    if not i == retries:
                        conn.terminal.pwarning(
                            f"({i}) Couldn't connect. Trying again in 5 seconds")
                        sleep(5)
                    else:
                        raise IceFlix.TemporaryUnavailable from temporary_error
        except IceFlix.Unauthorized:
            conn.terminal.perror('Wrong username/password combination')

    @staticmethod
    def get_catalog_name(conn : ActiveConnection, name : str, exact : bool):
        '''
            Tries to get a tile by its name from the catalog services
        '''
        catalog = conn.get_catalog()

        logging.info('Fetching tiles %s %s', 'EXACT' if exact else 'NOT EXACT', name)
        titles = catalog.getTilesByName(name, exact)
        logging.info('Got %d tiles', len(titles))
        if not titles:
            if exact:
                conn.terminal.perror(f'None of the media is titled: {name}')
            else:
                conn.terminal.perror(f'None of the media contains: {name}')
            return
        pmedia = {_id: PartiaMedia(_id, name=name) for _id in titles}
        Commands.save_pmedia(conn, pmedia)
        Commands.show_titles(conn, pmedia)

    @staticmethod
    def get_catalog_tags(conn : ActiveConnection, tags : list[str], include_all : bool):
        '''
            Tries to get a tile by its tags from the catalog services
        '''
        catalog = conn.get_catalog()

        logging.info('Fetching %s %s', 'INCLUDE ALL' if include_all else 'NOT INCLUDE ALL', tags)
        titles = catalog.getTilesByTags(tags, include_all, conn.terminal.session.token)
        logging.info('Got %d tiles', len(titles))
        if not titles:
            title_tags = ', '.join(tags)
            if include_all:
                conn.terminal.perror(f'No media found with tags: {title_tags}')
            else:
                conn.terminal.perror(f'None of the media contains: {title_tags}')
            return
        buffer = {id: PartiaMedia(id, tags=tags) for id in titles}
        Commands.save_pmedia(conn, buffer)
        Commands.show_titles(conn, buffer)

    @staticmethod
    def use_title(conn : ActiveConnection, title_id : str):
        '''
            Allows the user to select a title to modify/download/remove it
        '''
        if title_id not in conn.terminal.session.cached_titles:
            return
        pmedia = conn.terminal.session.cached_titles[title_id]
        conn.terminal.session.selected_title = pmedia
        conn.terminal.poutput(f'Selected: {pmedia}')

    @staticmethod
    def save_pmedia(conn : ActiveConnection, media : dict[str, PartiaMedia]):
        '''
            Saves a dictionary of media to the user cache
        '''
        union = set(conn.terminal.session.cached_titles).intersection(media)
        for title_id in union:
            updated = media[title_id]
            cached = conn.terminal.session.cached_titles[title_id]
            updated.name = cached.name if updated.name is None else updated.name
            updated.tags = cached.tags if updated.tags is None else updated.tags

        logging.debug('Saved tiles: %s', media)
        conn.terminal.session.cached_titles.update(media)

    @staticmethod
    def show_titles(conn : ActiveConnection, titles : dict[str, PartiaMedia]):
        '''
            Prints all the media in titles
        '''
        buffer = ''
        for pmedia in titles.values():
            buffer += f'{pmedia}\n'
        if not buffer:
            conn.terminal.perror('No media to show')
            return
        conn.terminal.poutput(buffer[:-1])

    @staticmethod
    def add_tags(conn : ActiveConnection, tags : list[str]):
        '''
            Add tags to the selected media
        '''
        catalog = conn.get_catalog()
        title = conn.terminal.session.selected_title
        if not title.tags:
            title.tags = []
        title.tags.extend(tags)
        title.tags = list(set(title.tags))
        catalog.addTags(title.id, tags, conn.terminal.session.token)
        logging.debug('Added tags to %s: %s', title.id, tags)

    @staticmethod
    def remove_tags(conn : ActiveConnection, tags : list[str]):
        '''
            Remove tags from the selected media
        '''
        title = conn.terminal.session.selected_title
        catalog = conn.get_catalog()
        if title.tags is not None:
            new_tags = list(set(title.tags).difference(tags))
            title.tags = None if not new_tags else new_tags
        catalog.removeTags(title.id, tags, conn.terminal.session.token)
        logging.debug('Removed tags from %s: %s', title.id, tags)

    @staticmethod
    def download(conn : ActiveConnection):
        '''
            Downloads a media from the media provider
        '''
        title = conn.terminal.session.selected_title
        media = title.fetch(conn)

        if not media:
            return

        if not media.provider:
            conn.terminal.perror("The title selected couldn't be downloaded")
            return

        logging.debug('Downloading from: %s', media.provider)

        session = conn.terminal.session
        handler = title.media.provider.openFile(title.id, session.token)
        with conn.terminal.terminal_lock:
            conn.terminal.poutput('Starting download...')
            time_initial = perf_counter_ns()
            with open(title.name, 'wb') as file:
                try:
                    while True:
                        try:
                            raw = handler.receive(2048, session.token)
                            if not raw:
                                break
                            logging.debug('%s', raw)
                            file.write(raw)
                        except IceFlix.Unauthorized:
                            logging.info('User token got rejected while downloading, refreshing...')
                            session.refresh(conn)
                except IceFlix.Unauthorized as unauthorized_error:
                    logging.info("Couldn't get a new valid user token, reverting download")
                    os.remove(title.name)
                    raise IceFlix.Unauthorized from unauthorized_error
                else:
                    time_end = perf_counter_ns()
                    final_time = (time_end - time_initial) / 10**9
                    logging.info('Download finished in %.2f seconds', final_time)
                    conn.terminal.poutput(
                        f"Finished downloading: '{title.name}' in {final_time:.2f} seconds"
                        )
                    handler.close(session.token)

    @staticmethod
    @ActiveConnection.needs_main
    def admin(conn : ActiveConnection):
        '''
            Authenticate an admin password and makes the user an admin if the password is correct
            If used at the beginning of a command, the user first becomes an admin,
            executes the command as admin and then the user loses its admin status
        '''
        config_admin_pass = conn.communicator.getProperties().getProperty('AdminToken')
        admin_pass = getpass('Admin password: ') if not config_admin_pass else config_admin_pass
        admin_sha256_pass = sha256(admin_pass.encode('utf-8')).hexdigest()
        auth = conn.get_authenticator()
        if not auth.isAdmin(admin_sha256_pass):
            conn.terminal.perror('Invalid password')
            return None
        conn.terminal.session.make_admin(admin_sha256_pass)
        return conn.terminal.session

    @staticmethod
    def add_user(conn : ActiveConnection, user : str, password : str):
        '''
            Adds an user to the authentication services
        '''
        auth = conn.get_authenticator()
        password_hash = sha256(password.encode('utf-8')).hexdigest()
        auth.addUser(user, password_hash, conn.terminal.session.admin_pass)
        logging.debug('User %s with password hash %s created', user, password_hash)
        conn.terminal.poutput(f'Added user {user}')

    @staticmethod
    def remove_user(conn : ActiveConnection, user : str):
        '''
            Removes an user from the authentication services
        '''
        auth = conn.get_authenticator()
        auth.removeUser(user, conn.terminal.session.admin_pass)
        logging.debug('User %s removed', user)
        conn.terminal.poutput(f'Removed user {user}')

    @staticmethod
    def rename(conn : ActiveConnection, name : str):
        '''
            Renames selected media
        '''
        title = conn.terminal.session.selected_title
        catalog = conn.get_catalog()
        catalog.renameTile(title.id, name, conn.terminal.session.admin_pass)
        title.name = name
        logging.debug('Title %s renamed to %s', title.id, name)
        conn.terminal.poutput(f'Title renamed to {name}')

    @staticmethod
    def remove(conn : ActiveConnection):
        '''
            Removes selected media
        '''
        title = conn.terminal.session.selected_title
        media = title.fetch(conn)

        if not media:
            return

        if not media.provider:
            conn.terminal.perror("The title selected couldn't be deleted, no provider associated")
            return

        logging.info('Removing tile %s', title.id)

        media.provider.removeFile(title.id, conn.terminal.session.admin_pass)
        conn.terminal.session.cached_titles.pop(title.id)
        conn.terminal.session.selected_title = None
        logging.debug('Removed tile %s from %s',  title.id, media.provider)
        conn.terminal.poutput(f'Removed {title.name}')

    @staticmethod
    def upload(conn : ActiveConnection, file : str):
        '''
            Upload a given file to the catalog
        '''
        with Ice.initialize() as uploader_comm:
            conn.terminal.poutput(f'Uploading file: {file}...')
            file_service = conn.get_file_service()
            file_uploader = FileUploaderApp(file, uploader_comm)
            file_uploader.main()
            cast = file_uploader.cast
            new_file_id = file_service.uploadFile(cast, conn.terminal.session.admin_pass)
            if new_file_id is None:
                conn.terminal.perror('No ID was assigned by the file service')
                return
            Commands.save_pmedia(conn, {new_file_id : PartiaMedia(new_file_id)})
            conn.terminal.poutput(f'Upload finished.\nThis file has the ID {new_file_id}')

class CliHandler(cmd2.Cmd):
    '''Handles user input via an interactive command line'''

    session : Session
    active_conn : ActiveConnection

    def __init__(self) -> None:
        self.active_conn = ActiveConnection(self)
        self.session = Session()
        shortcuts = dict(cmd2.DEFAULT_SHORTCUTS)

        shortcuts.update({'sudo': 'admin'})
        super().__init__(shortcuts=shortcuts)

        self.debug = True

        self.prompt = self.get_prompt()

    @staticmethod
    def need_creds(func):
        '''
            Only runs the command if the user is authenticated
        '''
        def check_creds(self, *args, **kwargs):
            if self.session.is_anon:
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
        '''
            Only runs the command if the user is admin
        '''
        def check_admin(self, *args, **kwargs):
            if not self.session.is_admin:
                self.perror('''This command needs administrative permissions
use the command 'admin' to obtain them''')
                return
            try:
                func(self, *args, **kwargs)
            except IceFlix.Unauthorized:
                self.perror('Your admin creedentials are invalid')
        check_admin.__name__ = func.__name__
        return check_admin

    @staticmethod
    def need_selected(func):
        '''
            Only runs the command if the user has selected a media
        '''
        def check_selected(self, *args, **kwargs):
            if self.session.selected_title is None:
                self.perror("First you need to select a title using 'catalog use id'")
                return
            func(self, *args, **kwargs)
        check_selected.__name__ = func.__name__
        return check_selected

    def get_user_consent(self, prompt) -> bool:
        '''
            Asks the user yes or no, returning True if yes else False
        '''
        return self.read_input(f'{prompt} [Yy/Nn]: ').lower() == "y"

    @cmd2.with_argparser(parsers.reconnect_parser)
    @cmd2.with_category("Utility")
    def do_reconnect(self, args):
        '''
            Reconnect to the main service, can be given a proxy
        '''
        prx = self.active_conn.proxy if args.proxy is None else args.proxy
        Commands.stablish_connection_main(self.active_conn, prx)

    @cmd2.with_category("Utility")
    def do_disconnect(self, _):
        '''
            Closes the connection to the main service, doesn't end the program execution
        '''
        self.active_conn.disconnect_topic_manager()
        self.session.make_user()

    @cmd2.with_category("Utility")
    def do_logout(self, _):
        '''
            Disconnects from the current user and allows to authenticate again
        '''
        self.session = Session()
        try:
            with self.terminal_lock:
                if self.get_user_consent('Wanna log in?'):
                    Commands.login(self.active_conn)
            return None
        except (KeyboardInterrupt, EOFError):
            self.poutput('')
            return True

    @cmd2.with_argparser(parsers.cat_base)
    @cmd2.with_category("Titles retrieving")
    def do_catalog(self, args):
        '''
            Catalog related set of commands
        '''
        func = getattr(args, 'func', None)
        if not func:
            return self.do_help('catalog')
        return func(self, args)

    def get_catalog(self, args):
        '''
            Retrieves titles by name or tag from the catalog service
        '''
        func = getattr(args, 'search_func', None)
        if not func:
            return self.do_help('catalog get')
        return func(self, args)

    def use_title(self, args):
        '''
            Allows the user to select a title from the titles cached
        '''
        Commands.use_title(self.active_conn, args.id)

    def search_name(self, args):
        '''
            Retrieves titles by name, can be exact or not
        '''
        Commands.get_catalog_name(self.active_conn, args.name, args.exact)

    @need_creds
    def search_tags(self, args):
        '''
            Retrieves titles by tags, can include all or not
        '''
        Commands.get_catalog_tags(self.active_conn, args.tags, args.include)

    def show_catalog(self, _):
        '''
            Shows currently cached titles
        '''
        Commands.show_titles(self.active_conn, self.session.cached_titles)

    parsers.cat_get_base.set_defaults(func=get_catalog)
    parsers.cat_show.set_defaults(func=show_catalog)

    parsers.cat_use.set_defaults(func=use_title)
    parsers.cat_name.set_defaults(search_func=search_name)
    parsers.cat_tags.set_defaults(search_func=search_tags)

    @cmd2.with_argparser(parsers.admin_parser)
    @cmd2.with_category("Utility")
    def do_admin(self, args):
        '''
            Transforms the user to admin
        '''
        if not self.session.is_admin:
            try:
                if not Commands.admin(self.active_conn):
                    return None
            except KeyboardInterrupt:
                self.poutput('')
                return None
            except EOFError:
                self.poutput('')
                return True
            called_as_admin = False
        else:
            called_as_admin = True
        if args.command:
            func = self.cmd_func(args.command)
            try:
                if not func:
                    self.default(args)
                else:
                    func(' '.join(args.arguments))
            finally:
                if not called_as_admin:
                    self.session.make_user()
        return None

    @cmd2.with_category("Utility")
    def do_exit(self, _):
        '''
            If the user is an admin removes permissions, if not the program ends
        '''
        if not self.session.is_admin:
            return True
        return self.session.make_user()

    @cmd2.with_argparser(parsers.users_parser_base)
    @cmd2.with_category("User management")
    @need_admin
    def do_users(self, args):
        '''
            Users related set of commands
        '''
        func = getattr(args, 'func', None)
        if not func:
            return self.do_help('catalog')
        return func(self, args)

    def users_add(self, args):
        '''
            Adds an user to the authentication service
        '''
        Commands.add_user(self.active_conn, args.user, args.password)

    def users_remove(self, args):
        '''
            Removes an user from the authentication service
        '''
        Commands.remove_user(self.active_conn, args.user)

    parsers.users_add.set_defaults(func=users_add)
    parsers.users_remove.set_defaults(func=users_remove)

    @cmd2.with_argparser(parsers.selected_parser_base)
    @cmd2.with_category("Title management")
    @need_selected
    def do_selected(self, args):
        '''
            Selected related set of commands
        '''
        func = getattr(args, 'func', None)
        if not func:
            return self.do_help('selected')
        return func(self, args)

    @need_admin
    def selected_rename(self, args):
        '''
            Rename selected title
        '''
        Commands.rename(self.active_conn, args.name)

    @need_creds
    def selected_tags(self, args):
        '''
            Allows to add or remove tags to the selected title
        '''
        func = getattr(args, 'action_func', None)
        if not func:
            return self.do_help('selected tags')
        return func(self, args)

    def tags_add(self, args):
        '''
            Adds tags to the selected title
        '''
        Commands.add_tags(self.active_conn, args.tags)

    def tags_remove(self, args):
        '''
            Removes tags from the selected title
        '''
        Commands.remove_tags(self.active_conn, args.tags)

    @need_creds
    def selected_download(self, _):
        '''
            Downloads the media
        '''
        Commands.download(self.active_conn)

    @need_admin
    def selected_remove(self, _):
        '''
            Remove the media
        '''
        Commands.remove(self.active_conn)

    parsers.rename_parser.set_defaults(func=selected_rename)
    parsers.tags_parser_base.set_defaults(func=selected_tags)
    parsers.download_parser.set_defaults(func=selected_download)
    parsers.remove_parser.set_defaults(func=selected_remove)

    parsers.add_tags.set_defaults(action_func=tags_add)
    parsers.remove_tags.set_defaults(action_func=tags_remove)

    def shutdown(self):
        '''
            Destroys the active communicator if it exists
        '''
        if self.active_conn._conn_check is not None:
            try:
                self.active_conn.disconnect_topic_manager()
            except Ice.ConnectionRefusedException:
                pass
        if self.active_conn.communicator is not None:
            self.active_conn.communicator.destroy()

    @cmd2.with_argparser(parsers.upload_parser)
    @cmd2.with_category("Title management")
    @need_admin
    def do_upload(self, args):
        '''
            Uploads a file to a file provider
        '''
        if not os.path.isfile(args.file):
            self.perror("Input file doesn't exists")
            return
        Commands.upload(self.active_conn, args.file)

    @cmd2.with_argparser(parsers.analyzer_parser)
    @cmd2.with_category("Utility")
    @need_admin
    def do_analyzetopics(self, args):
        '''
            Allows an administrator user to see what's happening at
            any topic channel used by IceFlix
        '''
        topics = args.topics if args.topics is not None else []
        if args.all:
            topics = list(event_listener.AvailableTopic)
        topics = list(set(topics).difference(args.ignore))
        if not topics:
            self.pwarning('[!] Empty topic list, showing help')
            return self.do_help('analyzetopics')
        stopics = ', '.join(topics) if topics else '-'
        self.pfeedback(f"Listening events from '{self.active_conn.proxy}'")
        self.poutput(f'Listening topics: {stopics}')
        self.pwarning('\nctrl+c to stop\n')
        self.poutput('-------------- Listening for events -------------')
        with event_listener.EventListenerApp(self.active_conn.proxy) as listener:
            for topic in topics:
                listener.subscribe(topic)
            listener.waitForShutdown()
        return None

    def get_prompt(self):
        '''
            Generates the cmd prompt
        '''
        media = '-#'
        title = self.session.selected_title
        if title is not None:
            media = f'{title.id}#' if title.name is None else f'{title.id}-{title.name}#'
        media = cmd2.ansi.style(media, fg=COLOR_SELECTED_TITLE)
        remote = self.active_conn.remote
        raw_text = f'{self.session.display_name}@{remote}:{media} '
        if not self.active_conn.reachable.is_set():
            color = COLORS.DISCONNECTED
        elif self.session.is_admin:
            color = COLORS.ADMIN
        elif self.session.is_anon:
            color = COLORS.ANON
        else:
            color = COLORS.USER
        return cmd2.ansi.style(f'{raw_text}', fg=color.value)

    def postcmd(self, stop, _):
        self.prompt = self.get_prompt()
        return stop

    def onecmd(self, *args, **kwargs):
        try:
            return super().onecmd(*args, **kwargs)
        except IceFlix.Unauthorized:
            self.perror("Unauthorized")
        except IceFlix.WrongMediaId:
            self.perror('The selected media seems to not exist on the catalog server')
        except IceFlix.TemporaryUnavailable:
            self.perror('This service is unavailable, try again later')
        except NoMainError:
            self.perror('No connection with the main server')
        except Ice.ConnectionRefusedException:
            self.perror('The service refused the connection')
        except Ice.ConnectionLostException:
            self.perror('Connection lost')
        except Ice.ConnectTimeoutException:
            self.perror('Connection timeout')
        except cmd2.exceptions.Cmd2ArgparseError as parser_error:
            raise parser_error
        except Exception as exception:
            self.perror('An unexpected error has occurred')
            self.pexcept(exception)
        return None

    def perror(self, msg: str = '', *, end: str = '\n', apply_style: bool = True) -> None:
        return super().perror(msg, end=end, apply_style=apply_style)
