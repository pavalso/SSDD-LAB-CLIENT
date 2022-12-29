#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import Ice
import IceStorm
import os

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix


class Publisher(Ice.Application):
    def run(self, argv):
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

        publisher = topic.getPublisher()
        printer = IceFlix.AnnouncementPrx.uncheckedCast(publisher)

        if not printer:
            raise RuntimeError("Invalid publisher proxy")

        printer.announce(topic_manager, '914')

        return 0


sys.exit(Publisher().main(sys.argv))