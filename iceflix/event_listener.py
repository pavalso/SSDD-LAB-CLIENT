#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
    Allows a client to connect to any topic from IceFlix and listen to all its events
'''

# pylint: disable=import-error, wrong-import-position, no-member, invalid-name

from threading import Lock
from enum import Enum
from datetime import datetime

import os
import Ice
import IceStorm

Ice.loadSlice(os.path.join(os.path.dirname(__file__), "iceflix.ice"))
import IceFlix


class AvailableTopic(str, Enum):
    '''
        Allowed topics
    '''
    Announcements = 'Announcements'
    UserUpdates = 'UserUpdates'
    CatalogUpdates = 'CatalogUpdates'
    FileAvailabilityAnnounce = 'FileAvailabilityAnnounce'

    def __str__(self) -> str:
        return self.name

class Event:
    '''
        Class used to store and event
    '''
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
        '''
            Wrapper for logging a event from a topic manager
        '''
        def decorator(func):
            def wrapper(*args, **kwargs):
                current = args[-1]
                _id = args[-2]
                event = Event(current, _id, interface.value)
                func(*args, event=event, **kwargs)
                print(str(event))
            return wrapper
        return decorator

class EventListener(
    IceFlix.Announcement, IceFlix.UserUpdate,
    IceFlix.CatalogUpdate, IceFlix.FileAvailabilityAnnounce):
    '''
        Listens to any event from any IceFlix topic
    '''
    @Event.log_event(AvailableTopic.Announcements)
    def announce(self, service: object, _id: str, _=None, event=None):
        '''
            Logs announce event
        '''
        service_type = service.ice_id()
        event.msg = f'announce self as {service_type}'

    @Event.log_event(AvailableTopic.UserUpdates)
    def newToken(self, user: str, token: str, _id: str, _=None, event=None):
        '''
            Logs newToken event
        '''
        event.msg = f'create token {token} for {user}'

    @Event.log_event(AvailableTopic.UserUpdates)
    def revokeToken(self, token: str, _id: str, _=None, event=None):
        '''
            Logs revokeToken event
        '''
        event.msg = f'revoke token {token}'

    @Event.log_event(AvailableTopic.UserUpdates)
    def newUser(self, user: str, passwordHash: str, _id: str, _=None, event=None):
        '''
            Logs newUser event
        '''
        event.msg = f'create user {user} with password hash {passwordHash}'

    @Event.log_event(AvailableTopic.UserUpdates)
    def removeUser(self, user: str, _id: str, _=None, event=None):
        '''
            Logs removeUser event
        '''
        event.msg = f'remove user {user}'

    @Event.log_event(AvailableTopic.CatalogUpdates)
    def renameTile(self, mediaId: str, newName: str, _id: str, _=None, event=None):
        '''
            Logs renameTile event
        '''
        event.msg = f'rename tile {mediaId} to {newName}'

    @Event.log_event(AvailableTopic.CatalogUpdates)
    def addTags(self, mediaId: str, user: str, tags: list[str], _id: str, _=None, event=None):
        '''
            Logs addTags event
        '''
        event.msg = f'add tags {tags} to the media {mediaId} for the user {user}'

    @Event.log_event(AvailableTopic.CatalogUpdates)
    def removeTags(self, mediaId: str, user: str, tags: list[str], _id: str, _=None, event=None):
        '''
            Logs removeTags event
        '''
        event.msg = f'remove tags {tags} from the media {mediaId} of the user {user}'

    @Event.log_event(AvailableTopic.FileAvailabilityAnnounce)
    def announceFiles(self, mediaIds: list[str], _id: str, _=None, event=None):
        '''
            Logs announceFiles event
        '''
        event.msg = f'announce {mediaIds}'

class EventListenerApp(Ice.Application):
    '''
        Initialize a new Event listener
    '''
    def __init__(self, topic_manager):
        super().__init__()
        self.comm = Ice.initialize()
        self.servant = EventListener()
        self.proxy = None
        self.adapter = None
        self.topic_manager = topic_manager
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
        '''
            Allows the servant to receive events for available_topic
        '''
        available_topic = str(available_topic)
        if self.topics[available_topic] is not None:
            return

        topic_manager = self.topic_manager

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
        '''
            Stops the servant from receiving events for available_topic
        '''
        available_topic = str(available_topic)
        topic = self.topics[available_topic]
        if topic is None:
            return
        topic.unsubscribe(self.proxy)
        self.topics[available_topic] = None

    def waitForShutdown(self):
        '''
            Wait until the event listener stops
        '''
        self.__lock.acquire()

    def shutdown(self):
        '''
            Stops the event listener and unsubscribe from all topics
        '''
        for available_topic in self.topics:
            self.unsubscribe(available_topic)
        self.__lock.release()
