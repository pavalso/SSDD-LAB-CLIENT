"""Module containing a template for a main service."""

import logging
import os
import sys

import Ice

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix

from time import sleep


class MediaCatalog(IceFlix.MediaCatalog):
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
        if not userToken == 'SECRET_TOKEN1':
            raise IceFlix.Unauthorized
        if not mediaId == '1':
            raise IceFlix.WrongMediaId
        return

    def removeTags(self, mediaId, tags, userToken, context):
        if not userToken == 'SECRET_TOKEN1':
            raise IceFlix.Unauthorized
        if not mediaId == '1':
            raise IceFlix.WrongMediaId
        return

    def renameTile(self, mediaId, name, adminToken, context):
        return

class MediaCatalogApp(Ice.Application):
    """Example Ice.Application for a Main service."""

    def __init__(self):
        super().__init__()
        self.servant = MediaCatalog()
        self.proxy = None
        self.adapter = None

    def run(self, args):
        """Run the application, adding the needed objects to the adapter."""
        logging.info("Running Media Catalog application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("CatalogAdapter")
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)

        sleep(5)
        print('Media catalog ready')
        with Ice.initialize(sys.argv) as communicator:
            base = communicator.stringToProxy('MainAdapter:tcp -p 9999')
            test = IceFlix.MainPrx.checkedCast(base)
            if not test:
                raise RuntimeError('Something bad happened')

            test.newService(IceFlix.MediaCatalogPrx.checkedCast(self.proxy), 'catalog')


        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        return 0

if __name__ == '__main__':
    app = MediaCatalogApp()
    sys.exit(app.main(sys.argv))
