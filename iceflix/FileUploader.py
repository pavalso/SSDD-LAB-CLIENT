import os

import Ice

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix


class FileUploader(IceFlix.FileUploader):
    def __init__(self, file) -> None:
        super().__init__()
        self.fp = open(file, 'rb')

    def receive(self, size, current):
        return self.fp.read(size)

    def close(self, current):
        if self.fp.closed:
            return
        self.fp.close()

class FileUploaderApp(Ice.Application):
    def __init__(self, file, comm):
        super().__init__()
        self.comm = comm
        self.servant = FileUploader(file)
        self.proxy = None
        self.adapter = None

    def main(self, configFile=None, initData=None):
        return super().main(['File Uploader'], configFile, initData)

    def run(self, args):
        self.adapter = self.comm.createObjectAdapterWithEndpoints('FileUploader', 'tcp')
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)

        self.cast = IceFlix.FileUploaderPrx.checkedCast(self.proxy)

        return 0
