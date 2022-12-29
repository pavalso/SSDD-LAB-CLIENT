#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

import Ice
import IceStorm
import os

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
#Ice.loadSlice("iceflix/iceflix.ice")
import IceFlix


class AnnouncementServant(IceFlix.Announcement):
    def announce(self, service: object, serviceId: str, current=None):
        print('announce')

class AnnouncementApp(Ice.Application):
    def run(self, argv):
        broker = self.communicator()
        servant = AnnouncementServant()

        adapter = broker.createObjectAdapterWithEndpoints('Announcements', 'tcp')
        proxy = adapter.addWithUUID(servant)

        print(proxy, flush=True)

        adapter.activate()

        topic_manager_str_prx = "IceStorm/TopicManager -t:tcp -h localhost -p 10000"
        topic_manager = IceStorm.TopicManagerPrx.checkedCast(
            self.communicator().stringToProxy(topic_manager_str_prx),
        )

        if not topic_manager:
            raise RuntimeError("Invalid TopicManager proxy")

        topic_name = "Announcements"
        try:
            topic = topic_manager.create(topic_name)
        except IceStorm.TopicExists:
            topic = topic_manager.retrieve(topic_name)

        qos = {}
        topic.subscribeAndGetPublisher(qos, proxy)

        self.shutdownOnInterrupt()
        broker.waitForShutdown()

        return 0


if __name__ == "__main__":
    server = AnnouncementApp()
    sys.exit(server.main(sys.argv))