#! /usr/bin/env python3
"""Wrap tkinter and related modules in a thread-safe API.

The tkinter package and related modules are unsafe for use with threads. Since
this can be a problem, the safe_tkinter package was written to overcome the
deficiency. Most imports of this module will use the import * syntax."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '15 December 2017'
__version__ = 1, 0, 0

import tkinter

from .gui import *
from .gui import __all__
from .thread_box import MetaBox

__all__ = __all__ + ['MetaBox']
tkinter.NoDefaultRoot()
