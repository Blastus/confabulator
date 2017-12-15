#! /usr/bin/env python3
"""Provide a way to run instance methods on a single thread.

This module allows hierarchical classes to be cloned so that their instances
run on one thread. Method calls are automatically routed through a special
execution engine. This is helpful when building thread-safe GUI code."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '15 December 2017'
__version__ = 1, 0, 2
__all__ = [
    'MetaBox'
]

import functools

from . import affinity


class BaseObject:
    __slots__ = '_MetaBox__exec', '__dict__'


class MetaBox(type):
    """MetaBox(name, bases, class_dict, old=None) -> MetaBox instance"""

    __REGISTRY = {object: BaseObject}
    __SENTINEL = object()

    @classmethod
    def clone(mcs, old, update=()):
        """Creates a class preferring thread affinity after update."""
        class_dict = dict(old.__dict__)
        class_dict.update(update)
        return mcs(old.__name__, old.__bases__, class_dict, old)

    @classmethod
    def thread(mcs, func):
        """Marks a function to be completely threaded when running."""
        func.__thread = mcs.__SENTINEL
        return func

    def __new__(mcs, name, bases, class_dict, old=None):
        """Allocates space for a new class after altering its data."""
        assert '__new__' not in class_dict, '__new__ must not be defined'
        assert '__slots__' not in class_dict, '__slots__ must not be defined'
        assert '__module__' in class_dict, '__module__ must be defined'
        # the previous asserts should be fine since this is a metaclass
        valid = []
        for base in bases:
            if base in mcs.__REGISTRY:
                valid.append(mcs.__REGISTRY[base])
            elif base in mcs.__REGISTRY.values():
                valid.append(base)
            else:
                valid.append(mcs.clone(base))
        for key, value in class_dict.items():
            if callable(value) and getattr(value, '_MetaBox__thread', None) \
                    is not mcs.__SENTINEL:
                class_dict[key] = mcs.__wrap(value)
        class_dict.update({
            '__new__': mcs.__new,
            '__slots__': (),
            '__module__': f'{__name__}.{class_dict["__module__"]}'
        })
        mcs.__REGISTRY[object() if old is None else old] = new = \
            super().__new__(mcs, name, tuple(valid), class_dict)
        return new

    # noinspection PyUnusedLocal
    def __init__(cls, name, bases, class_dict, old=None):
        """Initializes class instance while ignoring the old class."""
        super().__init__(name, bases, class_dict)

    @staticmethod
    def __wrap(func):
        """Wraps a method so execution runs via an affinity engine."""

        @functools.wraps(func)
        def box(self, *args, **kwargs):
            return self.__exec(func, self, *args, **kwargs)

        return box

    @classmethod
    def __new(mcs, cls, *args, **kwargs):
        """Allocates space for instance and finds __exec attribute."""
        self = object.__new__(cls)
        if 'master' in kwargs:
            self.__exec = kwargs['master'].__exec
        else:
            valid = tuple(mcs.__REGISTRY.values())
            for value in args:
                if isinstance(value, valid):
                    self.__exec = value.__exec
                    break
            else:
                self.__exec = affinity.Affinity()
        return self
