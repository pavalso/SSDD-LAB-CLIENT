#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import Ice
import IceStorm
import os
import logging

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
            return logging.info('Ignored announce from %s', serviceId)
        self.__timer.reset()
        self._conn_ref.main = main
        logging.info('Using main %s', main)

    def _timedout(self):
        if self._conn_ref.main is None:
            return
        logging.debug('Connection to %s timedout', self._conn_ref.main)
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
        logging.debug("'%s' connection checker created", self.proxy)

        return 0

    def subscribe_to_proxy(self, topic_manager_str_prx: str):
        topic_manager = IceStorm.TopicManagerPrx.checkedCast(
            self.comm.stringToProxy(topic_manager_str_prx),
        )
        logging.debug("Connected to topic manager '%s'", topic_manager)

        if not topic_manager:
            raise RuntimeError("Invalid TopicManager proxy")

        topic_name = "Announcements"
        try:
            topic = topic_manager.create(topic_name)
            logging.debug('Topic %s created', topic_name)
        except IceStorm.TopicExists:
            topic = topic_manager.retrieve(topic_name)
            logging.debug('Topic %s retrieved', topic_name)

        self._unsubscribe()
        self._topic = topic

        qos = {}
        self._topic.subscribeAndGetPublisher(qos, self.proxy)
        logging.debug('Subscribed to %s', self._topic)

    def _unsubscribe(self):
        if self._topic is not None:
            self._topic.unsubscribe(self.proxy)
            logging.debug('Unsubscribed from %s', self._topic)

    def disconnect(self):
        self._unsubscribe()
        self.servant._conn_ref.main = None
        logging.info('Connection checker disconnected')
