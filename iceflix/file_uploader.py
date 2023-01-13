'''
    Manages the file transfer
'''

# pylint: disable=import-error, wrong-import-position, consider-using-with

import os
import logging

import Ice

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix


class FileUploader(IceFlix.FileUploader):
    '''File uploader Ice servant'''
    def __init__(self, file) -> None:
        super().__init__()
        self.file_pointer = open(file, 'rb')
        logging.info('Sending file: %s', file)

    def receive(self, size, _):
        '''Gets size bytes from the file and returns them'''
        raw = self.file_pointer.read(size)
        logging.debug('%s', raw)

    def close(self, _):
        '''Closes the file and shutdowns the uploader'''
        if self.file_pointer.closed:
            return
        self.file_pointer.close()
        logging.info('Close received')

class FileUploaderApp(Ice.Application):
    '''Manages the file transfer'''
    def __init__(self, file, comm):
        super().__init__()
        self.comm = comm
        self.servant = FileUploader(file)
        self.proxy = None
        self.adapter = None
        self.cast = None

    def main(self, _=None, configFile=None, initData=None):
        return super().main(['File Uploader'], configFile, initData)

    def run(self, _):
        self.adapter = self.comm.createObjectAdapterWithEndpoints('FileUploader', 'tcp')
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)

        self.cast = IceFlix.FileUploaderPrx.checkedCast(self.proxy)

        return 0
