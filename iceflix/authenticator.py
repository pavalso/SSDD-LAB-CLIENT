"""Module containing a template for a main service."""

import logging
import os
import sys
from time import sleep

import Ice

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix


class Authenticator(IceFlix.Authenticator):
    def refreshAuthorization(self, user, passwordHash, context):
        #raise IceFlix.Unauthorized
        return 'SECRET_TOKEN'

    def isAuthorized(userToken):
        pass

    def whois(userToken):
        raise IceFlix.Unauthorized
    
    def isAdmin(self, adminToken, context):
        from hashlib import sha256
        return adminToken == sha256(b'secret').hexdigest()
    
    def addUser(self, user, passwordHash, adminToken, context):
        return
        raise IceFlix.Unauthorized() 
        raise IceFlix.TemporaryUnavailable()
    
    def removeUser(self, user, adminToken, context): 
        return
        raise IceFlix.Unauthorized()
        raise IceFlix.TemporaryUnavailable()


class AuthenticatorApp(Ice.Application):
    """Example Ice.Application for a Main service."""

    def __init__(self):
        super().__init__()
        self.servant = Authenticator()
        self.proxy = None
        self.adapter = None

    def run(self, args):
        """Run the application, adding the needed objects to the adapter."""
        logging.info("Running Authenticator application")
        comm = self.communicator()
        self.adapter = comm.createObjectAdapter("AuthenticatorAdapter")
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)

        sleep(5)
        print('Auth ready')
        with Ice.initialize(sys.argv) as communicator:
            base = communicator.stringToProxy('MainAdapter:tcp -p 9999')
            test = IceFlix.MainPrx.checkedCast(base)
            if not test:
                raise RuntimeError('Something bad happened')

            test.newService(IceFlix.AuthenticatorPrx.checkedCast(self.proxy), 'authenticator')

        self.shutdownOnInterrupt()
        comm.waitForShutdown()

        return 0

if __name__ == '__main__':
    app = AuthenticatorApp()
    sys.exit(app.main(sys.argv))