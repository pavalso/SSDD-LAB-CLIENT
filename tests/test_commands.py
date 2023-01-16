from tests import Main, Authenticator, Catalog
import iceflix.commands

import os

import unittest   # The test framework
import Ice
import datetime

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "../iceflix/iceflix.ice"))
import IceFlix


class TestCli(unittest.TestCase):
    def setUp(self) -> None:
        self.main = Main()
        self.main.authenticator = Authenticator()
        self.main.catalog = Catalog()
        self.cmd = iceflix.commands.CliHandler()
        self.cmd.active_conn._conn_check.servant.announce(self.main, 'test')
        self.cmd.active_conn._conn_check.servant.mains[self.main] = datetime.datetime(9999, 12, 30)

    def test_reconnect(self):
        self.cmd.do_reconnect('')
        self.cmd.do_reconnect('-p "proxy"')
        with self.assertRaises(Ice.ConnectionRefusedException):
            self.cmd.do_reconnect('-p "proxy:tcp"')

    def test_disconnect(self):
        self.cmd.do_disconnect('')
        with self.assertRaises(iceflix.commands.NoMainError):
            self.cmd.do_catalog('get name a_tile')
#pytest --cov iceflix
#pip install pytest-cov
    def test_login(self):
        self.assertIsNotNone(self.cmd.active_conn.main)
        self.cmd.read_input = lambda *_, **__: 'n'
        self.cmd.do_logout('')
        self.assertTrue(self.cmd.session.is_anon)
        self.assertIsNone(self.cmd.session.token)
        self.assertFalse(self.cmd.session.is_admin)
        self.cmd.read_input = lambda *_, **__: 'y'
        iceflix.commands.getpass = lambda *_, **__: 'unauthorized'
        self.cmd.do_logout('')
        self.assertIsNone(self.cmd.session.token)
        iceflix.commands.getpass = lambda *_, **__: 'temp_unavailable'
        with self.assertRaises(IceFlix.TemporaryUnavailable):
            self.cmd.do_logout('')
        iceflix.commands.getpass = lambda *_, **__: 'a_valid_password'
        self.cmd.do_logout('')
        self.assertFalse(self.cmd.session.is_anon)
        self.assertIsNotNone(self.cmd.session.token)
        self.assertFalse(self.cmd.session.is_admin)

    def test_catalog(self):
        self.assertIsNotNone(self.cmd.active_conn.main)
        self.cmd.do_catalog('get name not_a_tile')
        self.assertFalse(self.cmd.session.cached_titles)
        self.cmd.do_catalog('get name valid_tile')
        self.assertEqual(len(self.cmd.session.cached_titles), 2)
        self.cmd.session.cached_titles = {}
        self.cmd.do_catalog('get name valid_tile --exact')
        self.assertEqual(len(self.cmd.session.cached_titles), 1)
        self.cmd.session.cached_titles = {}
        self.cmd.read_input = lambda *_, **__: 'y'
        iceflix.commands.getpass = lambda *_, **__: 'a_password'
        self.cmd.do_logout('')
        self.cmd.do_catalog('get tags tag_1')
        self.assertEqual(len(self.cmd.session.cached_titles), 1)
        self.cmd.session.cached_titles = {}
        self.cmd.do_catalog('get tags tag_1 tag_2')
        self.assertEqual(len(self.cmd.session.cached_titles), 2)
        self.cmd.session.cached_titles = {}
        self.cmd.do_catalog('get tags tag_1 tag_2 --include')
        self.assertEqual(len(self.cmd.session.cached_titles), 1)
        self.cmd.session.cached_titles = {}
        self.cmd.do_catalog('get tags tag_1 tag_2 tag_3 --include')
        self.assertFalse(self.cmd.session.cached_titles)
        self.cmd.do_catalog('show')
        self.cmd.do_catalog('use title_1')

    def test_selected(self):
        self.assertIsNotNone(self.cmd.active_conn.main)
        pm = iceflix.commands.PartiaMedia('tile_1')
        self.cmd.do_selected('rename new_tile_name')
        self.cmd.session.refresh(self.cmd.active_conn)
        self.cmd.session.selected_title = pm
        self.cmd.do_selected('tags')
        self.cmd.do_selected('tags add tag_5 tag_6')
        self.cmd.do_selected('tags remove tag_5')
        pm = iceflix.commands.PartiaMedia(None)
        self.cmd.session.selected_title = pm
        with self.assertRaises(IceFlix.WrongMediaId):
            self.cmd.do_selected('tags add tag_5 tag_6')
            self.cmd.do_selected('tags remove tag_5')

    def test_admin(self):
        self.assertIsNotNone(self.cmd.active_conn.main)
        iceflix.commands.getpass = lambda *_, **__: 'not_the_password'
        self.cmd.do_admin('')
        self.assertFalse(self.cmd.session.is_admin)
        iceflix.commands.getpass = lambda *_, **__: 'secret'
        self.cmd.do_admin('')
        self.assertTrue(self.cmd.session.is_admin)
        self.assertFalse(self.cmd.do_exit(''))
        self.assertFalse(self.cmd.session.is_admin)
        self.assertTrue(self.cmd.do_exit(''))
        # Test admin commands

    def tearDown(self) -> None:
        self.cmd.shutdown()
