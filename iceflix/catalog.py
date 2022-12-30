"""Module containing a template for a main service."""

import logging
import sys
import secrets

import Ice
import IceStorm

import IceFlix

from threading import Thread

authenticator = None
catalog = None
fileService = None


user_update = None
id = 0

class Catalog(IceFlix.MediaCatalog):
    """Servant for the IceFlix.Main interface.
    Disclaimer: this is demo code, it lacks of most of the needed methods
    for this interface. Use it with caution
    """

    def getTile(self, mediaId, userToken, context):
        media = IceFlix.Media(
            '1',
            None,
            IceFlix.MediaInfo(
                'gola',
                 ['tuya', 'muya']
            )
        )
        #if not userToken == 'SECRET_TOKEN':
        #    raise IceFlix.Unauthorized
        #raise IceFlix.TemporaryUnavailable
        if not mediaId == media.mediaId:
            raise IceFlix.WrongMediaId
        return media
        

    def getTilesByName(self, name, exact, context):
        if name == 'gola':
            return ['1']
        return []

    def getTilesByTags(self, tags, includeAllTags, userToken, context):
        print(userToken)
        if not userToken == 'SECRET_TOKEN':
            raise IceFlix.Unauthorized
        if includeAllTags and tags == ['tuya', 'muya']:
            return ['1']
        elif not includeAllTags and ('tuya' in tags or 'muya' in tags):
            return ['1']
        return []

    def addTags(self, mediaId, tags, userToken, context):
        if not userToken == 'SECRET_TOKEN':
            raise IceFlix.Unauthorized
        if not mediaId == '1':
            raise IceFlix.WrongMediaId
        user_update.addTags(mediaId, userToken, tags, id)
        return

    def removeTags(self, mediaId, tags, userToken, context):
        if not userToken == 'SECRET_TOKEN':
            raise IceFlix.Unauthorized
        if not mediaId == '1':
            raise IceFlix.WrongMediaId
        user_update.removeTags(mediaId, userToken, tags, id)
        return

    def renameTile(self, mediaId, name, adminToken, context):
        user_update.renameTile(mediaId, name, id)
        return

class CatalogApp(Ice.Application):
    """Example Ice.Application for a Main service."""

    def __init__(self):
        global id
        super().__init__()
        self.servant = Catalog()
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
        global user_update
        """Run the application, adding the needed objects to the adapter."""
        logging.info("Running Catalog application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("CatalogAdapter")
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

        topic_name = "CatalogUpdates"
        try:
            ouput_events = topic_manager.create(topic_name)
        except IceStorm.TopicExists:
            ouput_events = topic_manager.retrieve(topic_name)
        publisher = ouput_events.getPublisher()
        user_update = IceFlix.CatalogUpdatePrx.uncheckedCast(publisher)

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        return 0

if __name__ == '__main__':
    app = CatalogApp()
    sys.exit(app.main(sys.argv))
