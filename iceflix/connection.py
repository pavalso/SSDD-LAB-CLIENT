#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import Ice
import IceStorm
import os

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix

try:
    from timedAction import TimedAction
except ImportError:
    from iceflix.timedAction import TimedAction

class ConnectionCheckerServant(IceFlix.Announcement):
    def __init__(self, conn_ref) -> None:
        super().__init__()
        self.__timer = TimedAction(12000, self._timedout)
        self.__timer.start()
        self._conn_ref = conn_ref

    def announce(self, service: object, serviceId: str, current=None):
        main = IceFlix.MainPrx.checkedCast(service)
        if main is None:
            return
        self.__timer.reset()
        self._conn_ref.main = main

    def _timedout(self):
        self._conn_ref.main = None

class ConnectionCheckerApp(Ice.Application):
    def __init__(self, comm, conn_ref):
        super().__init__()
        self.comm = comm
        self.servant = ConnectionCheckerServant(conn_ref)
        self.proxy = None
        self.adapter = None
        self._topic = None

    def main(self, _=None, configFile=None, initData=None):
        return super().main(['Connection Checker'], configFile, initData)

    def run(self, _):
        self.adapter = self.comm.createObjectAdapterWithEndpoints('Announcements', 'tcp')
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)

        return 0

    def subscribe_to_proxy(self, topic_manager_str_prx: str):
        self._unsubscribe()

        topic_manager = IceStorm.TopicManagerPrx.checkedCast(
            self.comm.stringToProxy(topic_manager_str_prx),
        )

        if not topic_manager:
            raise RuntimeError("Invalid TopicManager proxy")

        topic_name = "Announcements"
        try:
            self._topic = topic_manager.create(topic_name)
        except IceStorm.TopicExists:
            self._topic = topic_manager.retrieve(topic_name)

        qos = {}
        self._topic.subscribeAndGetPublisher(qos, self.proxy)

    def _unsubscribe(self):
        if self._topic is not None:
            self._topic.unsubscribe(self.proxy)

    def disconnect(self):
        self._unsubscribe()
        self.servant._conn_ref.main = None
