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

    Ice.loadSlice(os.path.join(os.path.dirname(__file__), "../iceflix/iceflix.ice"))
import IceFlix


from threading import Thread


class Main(IceFlix.Main, IceFlix.Announcement):
    """Servant for the IceFlix.Main interface.

    Disclaimer: this is demo code, it lacks of most of the needed methods
    for this interface. Use it with caution
    """
    
    authenticator = None
    catalog = None
    fileService = None

    def getAuthenticator(self, current):
        if self.authenticator is None:
            raise IceFlix.TemporaryUnavailable()
        return self.authenticator

    def getCatalog(self, current):
        if self.catalog is None:
            raise IceFlix.TemporaryUnavailable()
        return self.catalog

    def getFileService(self, current):
        if self.fileService is None:
            raise IceFlix.TemporaryUnavailable()
        return self.fileService

    def announce(self, service: object, serviceId: str, current=None):
        auth = IceFlix.AuthenticatorPrx.checkedCast(service)
        if auth is not None:
            self.authenticator = auth
        cat = IceFlix.MediaCatalogPrx.checkedCast(service)
        if cat is not None:
            self.catalog = cat
        file = IceFlix.FileServicePrx.checkedCast(service)
        if file is not None:
            self.fileService = file

class MainApp(Ice.Application):
    """Example Ice.Application for a Main service."""

    def __init__(self):
        super().__init__()
        self.servant = Main()
        self.proxy = None
        self.adapter = None
        self.id = secrets.token_hex(16)

    def announce_self(self):
        from time import sleep
        while True:
            publisher = self.topic.getPublisher()
            announce = IceFlix.AnnouncementPrx.uncheckedCast(publisher)
            announce.announce(self.proxy, self.id)
            sleep(10)

    def run(self, args):
        """Run the application, adding the needed objects to the adapter."""
        logging.info("Running Main application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("MainAdapter")
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)
        print(self.proxy)

        topic_manager = IceStorm.TopicManagerPrx.checkedCast(
            comm.stringToProxy("IceStorm/TopicManager -t:tcp -h 192.168.1.204 -p 10000"),
        )

        if not topic_manager:
            raise RuntimeError("Invalid TopicManager proxy")

        topic_name = "Announcements"
        try:
            self.topic = topic_manager.create(topic_name)
        except IceStorm.TopicExists:
            self.topic = topic_manager.retrieve(topic_name)

        qos = {}
        self.topic.subscribeAndGetPublisher(qos, self.proxy)

        Thread(target=self.announce_self, daemon=True).start()
        
        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        return 0

if __name__ == '__main__':
    app = MainApp()
    sys.exit(app.main(sys.argv))
