import iceflix.commands
import iceflix.test_objects

import os

import unittest   # The test framework
import Ice
import datetime

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix


class TestCli(unittest.TestCase):
    def setUp(self) -> None:
        self.main = iceflix.test_objects.Main()
        self.main.authenticator = iceflix.test_objects.Authenticator()
        self.main.catalog = iceflix.test_objects.Catalog()
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

    def test_login(self):        
        self.cmd.read_input = lambda *_, **__: 'n'
        self.cmd.do_logout('')
        self.assertTrue(self.cmd.session.is_anon)
        self.assertIsNone(self.cmd.session.token)
        self.assertFalse(self.cmd.session.is_admin)
        self.cmd.read_input = lambda *_, **__: 'y'
        iceflix.commands.getpass = lambda *_, **__: 'a_password'
        self.cmd.do_logout('')
        self.assertFalse(self.cmd.session.is_anon)
        self.assertIsNotNone(self.cmd.session.token)
        self.assertFalse(self.cmd.session.is_admin)

    def test_catalog(self):
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

    def test_admin(self):
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
