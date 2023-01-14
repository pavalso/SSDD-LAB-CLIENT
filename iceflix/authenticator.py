"""Module containing a template for a main service."""

import logging
import sys
import secrets

import Ice
import IceStorm


try:
    import IceFlix

except ImportError:
    import os
    import Ice

    Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix
from threading import Thread

authenticator = None
catalog = None
fileService = None


user_update = None
id = 0

class Authenticator(IceFlix.Authenticator):
    def refreshAuthorization(self, user, passwordHash, context):
        #raise IceFlix.Unauthorized
        user_update.newToken(user, 'SECRET_TOKEN', id)
        return 'SECRET_TOKEN'

    def isAuthorized(userToken):
        pass

    def whois(userToken):
        raise IceFlix.Unauthorized
    
    def isAdmin(self, adminToken, context):
        from hashlib import sha256
        return adminToken == sha256(b'secret').hexdigest()
    
    def addUser(self, user, passwordHash, adminToken, context):
        user_update.newUser(user, passwordHash, id)
        return
        raise IceFlix.Unauthorized() 
        raise IceFlix.TemporaryUnavailable()
    
    def removeUser(self, user, adminToken, context):
        user_update.removeUser(user, id)
        return
        raise IceFlix.Unauthorized()
        raise IceFlix.TemporaryUnavailable()

class AuthenticatorApp(Ice.Application):
    """Example Ice.Application for a Main service."""

    def __init__(self):
        global id
        super().__init__()
        self.servant = Authenticator()
        self.proxy = None
        self.adapter = None
        self.id = secrets.token_hex(16)
        id = self.id

    def announce_self(self):
        from time import sleep
        while True:
            publisher = self.topic.getPublisher()
            announce = IceFlix.AnnouncementPrx.uncheckedCast(publisher)
            announce.announce(self.proxy, self.id)
            sleep(10)

    def run(self, args):
        """Run the application, adding the needed objects to the adapter."""
        global user_update
        logging.info("Running Auth application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("AuthenticatorAdapter")
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)
        print(self.proxy)

        topic_manager = IceStorm.TopicManagerPrx.checkedCast(
            comm.stringToProxy("IceStorm/TopicManager -t:tcp -h localhost -p 10000"),
        )

        if not topic_manager:
            raise RuntimeError("Invalid TopicManager proxy")

        topic_name = "Announcements"
        try:
            self.topic = topic_manager.create(topic_name)
        except IceStorm.TopicExists:
            self.topic = topic_manager.retrieve(topic_name)

        Thread(target=self.announce_self, daemon=True).start()

        topic_name = "UserUpdates"
        try:
            ouput_events = topic_manager.create(topic_name)
        except IceStorm.TopicExists:
            ouput_events = topic_manager.retrieve(topic_name)
        publisher = ouput_events.getPublisher()
        user_update = IceFlix.UserUpdatePrx.uncheckedCast(publisher)

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        return 0

if __name__ == '__main__':
    app = AuthenticatorApp()
    sys.exit(app.main(sys.argv))
