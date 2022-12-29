'''
    https://github.com/pavalso/Timed-Actions
'''

from threading import Thread, current_thread
from time import sleep
from datetime import datetime
from typing import Callable


def now() -> float:
    '''
        Current time as milliseconds
    '''
    return datetime.now().timestamp() * 1000

class _Waiter:
    '''
        If not reseted, executes the action else waits for the left time
    '''
    _ms: int

    _target_time: float = 0
    _starting_time: float = 0
    _last_wait_time: float = 0
    
    _action: Callable

    __execute: bool = True

    __t: Thread = None

    def __init__(self, ms: int, action: Callable) -> None:
        self._ms = ms
        self._action = action

    def __tFunc(self, *args, **kwargs):
        _ct = current_thread()
        self._last_wait_time = 0

        while True:
            _wt = self._target_time - now()
            self._last_wait_time += _wt
            
            self.__execute = True
            sleep(_wt / 1000)

            if _ct is not self.__t:
                return

            if self.__execute:
                self._action(*args, **kwargs)
                self._last_wait_time = 0
                self._target_time = self.__next_target_time()

    def start(self, *args, **kwargs):
        '''
            Sets all initial variables and starts __tFunc asynchronously
            Should only be called once
        '''
        self._starting_time = now()
        self._target_time = self._starting_time + self._ms
        self.__t = Thread(target=self.__tFunc, args=args, kwargs=kwargs, daemon=True)
        self.__t.start()

    def stop(self):
        '''
            Prevents the next wait from running, then destroys the thread
        '''
        self.__t = None

    def reset(self):
        '''
            Makes the thread execute in now + _ms milliseconds
        '''
        self._target_time = self.__next_target_time()
        self.__execute = False

    def __next_target_time(self) -> float:
        return now() + self._ms

class TimedAction:
    '''
        Allows an action to be executed repeatly until stop is called, for the action to be executed, the program must run for milliseconds
    '''
    _waiter: _Waiter

    @property
    def last_wait_time_ms(self) -> float:
        return self._waiter._last_wait_time

    @property
    def last_wait_time_s(self) -> float:
        return self._waiter._last_wait_time / 1000

    def __init__(self, milliseconds: int, action: Callable) -> None:
        self._waiter = _Waiter(milliseconds, action)

    def start(self, *args, **kwargs):
        '''
            Starts waiting for milliseconds, all function parameters are passed to the action call
            Should be called only once
        '''
        self._waiter.start(*args, **kwargs)

    def stop(self):
        '''
            Finishes waiting and prevents further execution of action
        '''
        self._waiter.stop()

    def reset(self):
        '''
            The action execution is delayed to current time + milliseconds
        '''
        self._waiter.reset()
