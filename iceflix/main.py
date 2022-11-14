"""Module containing a template for a main service."""

import logging
import os
import sys

import Ice

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix


class Main(IceFlix.Main):
    """Servant for the IceFlix.Main interface.

    Disclaimer: this is demo code, it lacks of most of the needed methods
    for this interface. Use it with caution
    """

    authenticator = None
    catalog = None

    def getAuthenticator(self, current):
        if Main.authenticator is None:
            raise IceFlix.TemporaryUnavailable()
        return Main.authenticator

    def getCatalog(self, current):
        if Main.catalog is None:
            raise IceFlix.TemporaryUnavailable()
        return Main.catalog
    
    def newService(self, object, service_id, current):
        if service_id == 'authenticator':
            Main.authenticator = IceFlix.AuthenticatorPrx.checkedCast(object)
        elif service_id == 'catalog':
            Main.catalog = IceFlix.MediaCatalogPrx.checkedCast(object)
        return
    
    def announce(self, object, service_id, current):
        # TODO: implement
        return


class MainApp(Ice.Application):
    """Example Ice.Application for a Main service."""

    def __init__(self):
        super().__init__()
        self.servant = Main()
        self.proxy = None
        self.adapter = None

    def run(self, args):
        """Run the application, adding the needed objects to the adapter."""
        logging.info("Running Main application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("MainAdapter")
        self.adapter.activate()

        #self.proxy = self.adapter.addWithUUID(self.servant)
        self.proxy = self.adapter.add(self.servant, comm.stringToIdentity("MainAdapter"))
        print(self.proxy)
        
        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        return 0

if __name__ == '__main__':
    app = MainApp()
    sys.exit(app.main(sys.argv))
