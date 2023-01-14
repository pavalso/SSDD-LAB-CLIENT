#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
    Check whenever a main has announced through icestorm topic manager and connects to it
'''

# pylint: disable=import-error, wrong-import-position, no-member

import os
import logging
import random
import datetime

import Ice
import IceStorm

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix


class ConnectionCheckerServant(IceFlix.Announcement):
    '''
        Receives announces from all IceFlix services and
        checks whenever no announce from a valid main has been received for 10 seconds and
        disconnects it
    '''

    def __init__(self, conn_ref) -> None:
        super().__init__()
        self._conn_ref = conn_ref
        self.mains = {}

    def get_main(self):
        '''
            Get a random unexpired and reachable main
        '''
        if not self.mains:
            return None
        main = random.choice(list(self.mains))
        expire_date = self.mains[main]
        delta = datetime.datetime.now() - expire_date
        refused = False
        try:
            main.ice_ping()
        except Ice.ConnectionRefusedException:
            refused = True
        if delta > datetime.timedelta(seconds=12) or refused:
            self.mains.pop(main)
            return self.get_main()
        return main

    def announce(self, service: object, serviceId: str, _=None):
        '''
            Announce callback for IceFlix.Announcement
        '''
        try:
            main = IceFlix.MainPrx.checkedCast(service)
        except:
            return None
        if main is None:
            return logging.info('Ignored announce from %s', serviceId)
        self.mains[main] = datetime.datetime.now()
        self._conn_ref.main = main
        return logging.info('Saved main %s', main)

    def _timedout(self):
        if self._conn_ref.main is None:
            return
        logging.debug('Connection to %s timedout', self._conn_ref.main)
        self._conn_ref.main = None

class ConnectionCheckerApp(Ice.Application):
    '''
        Service for subscribing to a specific topic_manager and get all the announces
    '''
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
        '''
            Subscribes to topic manager at topic_manager_str_prx
        '''
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
        '''
            Disconnects from current topic manager
        '''
        self._unsubscribe()
        self.servant._conn_ref.main = None
        logging.info('Connection checker disconnected')
