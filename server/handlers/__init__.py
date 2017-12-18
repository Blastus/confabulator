#! /usr/bin/env python3
"""Package that organizes server handlers into smaller, related groupings.

Created to be similar to the safe_tkinter package, this file provides the
public API to server handlers and groups them by related functionality. None
of the underlying modules should need to be imported by programmers."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '18 December 2017'
__version__ = 1, 0, 0

from .external import *
from .external import __all__
from .internal import enum

__all__ = __all__ + ['enum']
