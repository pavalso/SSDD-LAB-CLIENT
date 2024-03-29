import iceflix.commands

import os
import random

import Ice

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "../iceflix/iceflix.ice"))
import IceFlix


class FileHandler(IceFlix.FileHandler):
    def __init__(self) -> None:
        super().__init__()
        self.buffer = random.randbytes(4096)

    def receive(self, size, current=None):
        raw, self.buffer = self.buffer[:size], self.buffer[size:]
        return raw
    
    def close(self, current=None):
        pass

class FileService(IceFlix.FileService):
    def openFile(self, mediaId, userToken, current=None):
        return FileHandler()

    def uploadFile(self, uploader, adminToken, current=None):
        while True:
            buf = uploader.receive(1024)
            if not buf:
                break
            print(buf)
        uploader.close()
        return 'tile_3'

    def removeFile(self, mediaId, adminToken, current=None):
        pass

MEDIA_1 = IceFlix.Media(
    'tile_1',
    FileService(),
    IceFlix.MediaInfo(
        'valid_tile',
         ['tag_1', 'tag_2']
    )
)

MEDIA_2 = IceFlix.Media(
    'tile_2',
    FileService(),
    IceFlix.MediaInfo(
        'valid_tile_2',
         ['tag_2', 'tag_3']
    )
)

class Catalog(IceFlix.MediaCatalog):
    """Servant for the IceFlix.Main interface.
    Disclaimer: this is demo code, it lacks of most of the needed methods
    for this interface. Use it with caution
    """

    def getTile(self, mediaId, userToken, current=None):
        if mediaId == 'tile_1':
            return MEDIA_1
        if mediaId == 'tile_2':
            return MEDIA_2
        raise IceFlix.WrongMediaId
        
    def getTilesByName(self, name, exact, current=None):
        if name == 'valid_tile':
            if exact:
                return ['tile_1']
            return ['tile_1', 'tile_2']
        if name == 'valid_tile_2':
            return ['valid_tile_2']
        return []

    def getTilesByTags(self, tags, includeAllTags, userToken, current=None):
        tags.sort()
        if includeAllTags:
            if tags == ['tag_1', 'tag_2']:
                return ['tile_1']
            if tags == ['tag_2', 'tag_3']:
                return ['tile_2']
        else:
            if tags == ['tag_1']:
                return ['tile_1']
            if tags == ['tag_1', 'tag_2'] or tags == ['tag_1', 'tag_3'] or tags == ['tag_2'] or tags == ['tag_2', 'tag_3']:
                return ['tile_1', 'tile_2']
            if tags == ['tag_3']:
                return ['tile_3']
        return []

    def addTags(self, mediaId, tags, userToken, current=None):
        if mediaId == 'tile_1' or mediaId == 'tile_2':
            return
        raise IceFlix.WrongMediaId

    def removeTags(self, mediaId, tags, userToken, current=None):
        if mediaId == 'tile_1' or mediaId == 'tile_2':
            return
        raise IceFlix.WrongMediaId

    def renameTile(self, mediaId, name, adminToken, current=None):
        return

class Authenticator(IceFlix.Authenticator):
    def refreshAuthorization(self, user, passwordHash, current=None):
        if iceflix.commands.sha256(b'unauthorized').hexdigest() == passwordHash:
            raise IceFlix.Unauthorized
        if iceflix.commands.sha256(b'temp_unavailable').hexdigest() == passwordHash:
            raise IceFlix.TemporaryUnavailable
        return 'SECRET_TOKEN'

    def isAuthorized(userToken):
        return

    def whois(userToken):
        raise IceFlix.Unauthorized
    
    def isAdmin(self, adminToken, current=None):
        return adminToken == iceflix.commands.sha256(b'secret').hexdigest() # Use same Hash function as client
    
    def addUser(self, user, passwordHash, adminToken, current=None):
        return
    
    def removeUser(self, user, adminToken, current=None):
        return

class Main(IceFlix.Main):
    """Servant for the IceFlix.Main interface.

    Disclaimer: this is demo code, it lacks of most of the needed methods
    for this interface. Use it with caution
    """
    
    authenticator = None
    catalog = None
    fileService = None

    def getAuthenticator(self, current=None):
        if self.authenticator is None:
            raise IceFlix.TemporaryUnavailable()
        return self.authenticator

    def getCatalog(self, current=None):
        if self.catalog is None:
            raise IceFlix.TemporaryUnavailable()
        return self.catalog

    def getFileService(self, current=None):
        if self.fileService is None:
            raise IceFlix.TemporaryUnavailable()
        return self.fileService

    def announce(self, service: object, serviceId: str, current=None):
        pass
