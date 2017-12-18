#! /usr/bin/env python3
"""Stores the definitions of several server data structures.

A server stores information while operating and requires an organized way to
to create, retrieve, update, and delete the underlying data. The following
structures assist in performing these requirements using a simple API."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '18 December 2017'
__version__ = 1, 0, 0
__all__ = [
    'ChannelLine',
    'Message'
]


class ChannelLine:
    """ChannelLine(source, message) -> ChannelLine instance"""

    def __init__(self, source, message):
        """Initialize structure with message and its source."""
        self.source = source
        self.message = message

    def echo(self, client):
        """Print a formatted line to the client."""
        client.print(f'[{self.source}] {self.message}')


class Message(ChannelLine):
    """Message(source, message) -> Message instance"""

    def __init__(self, source, message):
        """Initialize message that includes new (read/unread) flag."""
        super().__init__(source, message)
        self.new = True
