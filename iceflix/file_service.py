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


class FileService(IceFlix.FileService):
    def openFile(self, mediaId, userToken, context):
        pass

    def uploadFile(self, uploader, adminToken, context):
        while True:
            buf = uploader.receive(1024)
            if not buf:
                break
            print(buf)
        uploader.close()
        return '2'

    def removeFile(self, mediaId, adminToken, context):
        pass

class FileServiceApp(Ice.Application):
    """Example Ice.Application for a Main service."""

    def __init__(self):
        super().__init__()
        self.servant = FileService()
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
        logging.info("Running FileService application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("FileService")
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

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        return 0

if __name__ == '__main__':
    app = FileServiceApp()
    sys.exit(app.main(sys.argv))
