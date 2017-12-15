#! /usr/bin/env python3
"""Allow a simple way to ensure execution is confined to one thread.

This module defines the Affinity data type that runs code on a single thread.
An instance of the class will execute functions only on the thread that made
the object in the first place. The class is useful in a GUI's main loop."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '15 December 2017'
__version__ = 1, 0, 1
__all__ = [
    'slots',
    'Affinity'
]

import inspect
import queue
import threading


def slots(names=''):
    """Set __slots__ variable in calling context with private names."""
    inspect.currentframe().f_back.f_locals['__slots__'] = tuple(
        f'__{name}' for name in names.replace(',', ' ').split()
    )


class Affinity:
    """Affinity() -> Affinity instance"""

    slots('thread, action')

    def __init__(self):
        """Initializes instance with thread identity and job queue."""
        self.__thread = threading.get_ident()
        self.__action = queue.Queue()

    def __call__(self, func, *args, **kwargs):
        """Executes function on creating thread and returns result."""
        if threading.get_ident() == self.__thread:
            while not self.__action.empty():
                self.__action.get_nowait()()
            return func(*args, **kwargs)
        delegate = Delegate(func, args, kwargs)
        self.__action.put_nowait(delegate)
        return delegate.value


class Delegate:
    """Delegate(func, args, kwargs) -> Delegate instance"""

    slots('func, args, kwargs, mutex, value, error')

    def __init__(self, func, args, kwargs):
        """Initializes instance from arguments and prepares to run."""
        self.__func = func
        self.__args = args
        self.__kwargs = kwargs
        self.__mutex = threading.Lock()
        self.__mutex.acquire()

    def __call__(self):
        """Executes code with arguments and allows value retrieval."""
        try:
            self.__value = self.__func(*self.__args, **self.__kwargs)
            self.__error = False
        except (TypeError, ValueError) as error:
            self.__value = error
            self.__error = True
        self.__mutex.release()

    @property
    def value(self):
        """Waits for value availability and raises or returns data."""
        self.__mutex.acquire()
        if self.__error:
            raise self.__value
        return self.__value
