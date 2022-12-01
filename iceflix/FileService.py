"""Module containing a template for a main service."""

import logging
import os
import sys
from time import sleep

import Ice

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix


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

    def run(self, args):
        """Run the application, adding the needed objects to the adapter."""
        logging.info("Running FileService application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("FileServiceAdapter")
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)

        sleep(5)
        print('FileService ready')
        with Ice.initialize(sys.argv) as communicator:
            base = communicator.stringToProxy('MainAdapter:tcp -p 9999')
            test = IceFlix.MainPrx.checkedCast(base)
            if not test:
                raise RuntimeError('Something bad happened')

            test.newService(IceFlix.FileServicePrx.checkedCast(self.proxy), 'fileService')

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        return 0
