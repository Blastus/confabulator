#! /usr/bin/env python3
"""Allow functions to be wrapped in a timeout API.

Since code can take a long time to run and may need to terminate before
finishing, this module provides a set_timeout decorator to wrap functions."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '18 December 2017'
__version__ = 1, 0, 1
__all__ = [
    'set_timeout',
    'run_with_timeout'
]

import multiprocessing
import sys
import time

DEFAULT_TIMEOUT = 60


def set_timeout(limit=None):
    """Return a wrapper that provides a timeout API for callers."""
    if limit is None:
        limit = DEFAULT_TIMEOUT
    _Timeout.validate_limit(limit)

    def wrapper(entry_point):
        return _Timeout(entry_point, limit)

    return wrapper


def run_with_timeout(limit, polling_interval, entry_point, *args, **kwargs):
    """Execute a callable object and automatically poll for results."""
    engine = set_timeout(limit)(entry_point)
    engine(*args, **kwargs)
    while engine.ready is False:
        time.sleep(polling_interval)
    return engine.value


def _target(queue, entry_point, *args, **kwargs):
    """Help with multiprocessing calls by being a top-level module function."""
    # noinspection PyPep8,PyBroadException
    try:
        queue.put((True, entry_point(*args, **kwargs)))
    except:
        queue.put((False, sys.exc_info()[1]))


class _Timeout:
    """_Timeout(entry_point, limit) -> _Timeout instance"""

    def __init__(self, entry_point, limit):
        """Initialize the _Timeout instance will all needed attributes."""
        self.__entry_point = entry_point
        self.__limit = limit
        self.__queue = multiprocessing.Queue()
        self.__process = multiprocessing.Process()
        self.__timeout = time.monotonic()

    def __call__(self, *args, **kwargs):
        """Begin execution of the entry point in a separate process."""
        self.cancel()
        self.__queue = multiprocessing.Queue(1)
        self.__process = multiprocessing.Process(
            target=_target,
            args=(self.__queue, self.__entry_point) + args,
            kwargs=kwargs
        )
        self.__process.daemon = True
        self.__process.start()
        self.__timeout = time.monotonic() + self.__limit

    def cancel(self):
        """Terminate execution if possible."""
        if self.__process.is_alive():
            self.__process.terminate()

    @property
    def ready(self):
        """Property letting callers know if a returned value is available."""
        if self.__queue.full():
            return True
        elif not self.__queue.empty():
            return True
        elif self.__timeout < time.monotonic():
            self.cancel()
        else:
            return False

    @property
    def value(self):
        """Property that retrieves a returned value if available."""
        if self.ready is True:
            valid, value = self.__queue.get()
            if valid:
                return value
            raise value
        raise TimeoutError('execution timed out before terminating')

    @property
    def limit(self):
        """Property controlling what the timeout period is in seconds."""
        return self.__limit

    @limit.setter
    def limit(self, value):
        self.validate_limit(value)
        self.__limit = value

    @staticmethod
    def validate_limit(value):
        """Verify that the limit's value is not too low."""
        if value <= 0:
            raise ValueError('limit must be greater than zero')
