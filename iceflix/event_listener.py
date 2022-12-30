#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import Ice
import IceStorm
import os

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix

from threading import Lock
from enum import Enum
from datetime import datetime


class AvailableTopic(str, Enum):
    Announcements = 'Announcements'
    UserUpdates = 'UserUpdates'
    CatalogUpdates = 'CatalogUpdates'
    FileAvailabilityAnnounce = 'FileAvailabilityAnnounce'

    def __str__(self) -> str:
        return self.name

class Event:
    timestamp: str
    interface: str
    event: str
    senderId: str
    msg: str = 'No message'

    def __init__(self, current, senderId, interface) -> None:
        self.timestamp = datetime.strftime(datetime.now(), '%m/%d/%Y %H:%M:%S')
        self.interface = interface
        self.event = current.operation
        self.senderId = senderId

    def __str__(self) -> str:
        return f'{self.timestamp} [{self.senderId}]->[{self.interface}.{self.event}]: {self.msg}'

    @staticmethod
    def log_event(interface: AvailableTopic):
        def decorator(func):
            def wrapper(*args, **kwargs):
                current = args[-1]
                serviceId = args[-2]
                event_log = Event(current, serviceId, interface.value)
                func(*args, event_log=event_log, **kwargs)
                print(str(event_log))
            return wrapper
        return decorator

class EventListener(
    IceFlix.Announcement, IceFlix.UserUpdate, 
    IceFlix.CatalogUpdate, IceFlix.FileAvailabilityAnnounce):
    @Event.log_event(AvailableTopic.Announcements)
    def announce(self, service: object, serviceId: str, current=None, event_log=None):
        service_type = service.ice_id()
        event_log.msg = f'announce self as {service_type}'

    @Event.log_event(AvailableTopic.UserUpdates)
    def newToken(self, user: str, token: str, serviceId: str, current=None, event_log=None):
       event_log.msg = f'create token {token} for {user}'

    @Event.log_event(AvailableTopic.UserUpdates)
    def revokeToken(self, token: str, serviceId: str, current=None, event_log=None):
        event_log.msg = f'revoke token {token}'

    @Event.log_event(AvailableTopic.UserUpdates)
    def newUser(self, user: str, passwordHash: str, serviceId: str, current=None, event_log=None):
        event_log.msg = f'create user {user} with password hash {passwordHash}'

    @Event.log_event(AvailableTopic.UserUpdates)
    def removeUser(self, user: str, serviceId: str, current=None, event_log=None):
        event_log.msg = f'remove user {user}'

    @Event.log_event(AvailableTopic.CatalogUpdates)
    def renameTile(self, mediaId: str, newName: str, serviceId: str, current=None, event_log=None):
        event_log.msg = f'rename tile {mediaId} to {newName}'

    @Event.log_event(AvailableTopic.CatalogUpdates)
    def addTags(self, mediaId: str, user: str, tags: list[str], serviceId: str, current=None, event_log=None):
        event_log.msg = f'add tags {tags} to the media {mediaId} for the user {user}'

    @Event.log_event(AvailableTopic.CatalogUpdates)
    def removeTags(self, mediaId: str, user: str, tags: list[str], serviceId: str, current=None, event_log=None):
        event_log.msg = f'remove tags {tags} from the media {mediaId} of the user {user}'

    @Event.log_event(AvailableTopic.FileAvailabilityAnnounce)
    def announceFiles(self, mediaIds: list[str], serviceId: str, current=None, event_log=None):
        event_log.msg = f'announce {mediaIds}'

class EventListenerApp(Ice.Application):
    def __init__(self, topic_manager_prx):
        super().__init__()
        self.comm = Ice.initialize()
        self.servant = EventListener()
        self.proxy = None
        self.adapter = None
        self.topic_manager_prx = topic_manager_prx
        self.__lock = Lock()

        self.topics = {str(topic): None for topic in AvailableTopic}

    def main(self, _=None, configFile=None, initData=None):
        return super().main(['Event Listener'], configFile, initData)

    def run(self, _):
        self.adapter = self.comm.createObjectAdapterWithEndpoints('Announcements', 'tcp')
        self.adapter.activate()

        self.proxy = self.adapter.addWithUUID(self.servant)

        self.__lock.acquire(blocking=False)
        return 0

    def __enter__(self):
        self.run(None)
        return self

    def __exit__(self, *args):
        self.shutdown()
        self.comm.destroy()

    def subscribe(self, available_topic: AvailableTopic):
        available_topic = str(available_topic)
        if self.topics[available_topic] is not None:
            return

        topic_manager = IceStorm.TopicManagerPrx.checkedCast(
            self.comm.stringToProxy(self.topic_manager_prx),
        )

        if not topic_manager:
            raise RuntimeError("Invalid TopicManager proxy")

        topic_name = available_topic

        try:
            topic = topic_manager.create(topic_name)
        except IceStorm.TopicExists:
            topic = topic_manager.retrieve(topic_name)

        qos = {}
        topic.subscribeAndGetPublisher(qos, self.proxy)
        self.topics[available_topic] = topic

    def unsubscribe(self, available_topic: AvailableTopic):
        available_topic = str(available_topic)
        topic = self.topics[available_topic]
        if topic is None:
            return
        topic.unsubscribe(self.proxy)
        self.topics[available_topic] = None

    def waitForShutdown(self):
        self.__lock.acquire()

    def shutdown(self):
        for available_topic in self.topics:
            self.unsubscribe(available_topic)
        self.__lock.release()

if __name__ == '__main__':
    with EventListenerApp('IceStorm/TopicManager -t:tcp -h localhost -p 10000') as app:
        app.subscribe(AvailableTopic.Announcements)
        app.subscribe(AvailableTopic.CatalogUpdates)
        app.subscribe(AvailableTopic.FileAvailabilityAnnounce)
        app.subscribe(AvailableTopic.UserUpdates)
        input()
