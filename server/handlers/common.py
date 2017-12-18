#! /usr/bin/env python3
"""Has the base class that all other server handlers inherit from.

The Handler class is partially inspired by the cmd.Cmd class in the standard
library. It is the basis for all handlers and is designed to provide an
automated way to run commands that have been set up on a handler."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '18 December 2017'
__version__ = 1, 0, 0
__all__ = [
    'STOP_WORDS',
    'YES_WORDS',
    'Handler',
]

import abc
import inspect
import json
import pickle

STOP_WORDS = frozenset({'exit', 'quit', 'stop'})
YES_WORDS = frozenset({'yes', 'true', '1'})


class Handler(abc.ABC):
    """Handler(client) -> Handler instance"""

    def __init__(self, client):
        """Initialize handler by saving client to public attribute."""
        self.client = client

    @abc.abstractmethod
    def handle(self):
        """Raise an error for calling this abstract method."""
        pass

    def command_loop(self, prompt='Command:'):
        """Handle commands received from the client."""
        mute = False
        while True:
            line = self.client.input() if mute else self.client.input(prompt)
            mute = False
            value = self.run_command(line)
            if value == '__json_help__':
                mute = True
            elif isinstance(value, AttributeError):
                self.client.print('Command not found!')
            elif isinstance(value, EOFError):
                return
            elif value is not None:
                return value

    def run_command(self, line):
        """Try running command with arguments based on line."""
        tokens = line.strip().split()
        if tokens:
            cmd, *args = tokens
            if cmd.endswith('__json_help__'):
                return self.json_help()
            if cmd == '?':
                cmd = 'help'
            try:
                func = getattr(self, 'do_' + cmd)
            except AttributeError as error:
                return error
            else:
                return func(args)

    def json_help(self):
        """Send client information on what commands are available."""
        package = {name: self.get_help(name) for name in self.commands}
        self.client.print(json.dumps(package))
        return '__json_help__'

    @property
    def commands(self):
        """Provide a list of commands the server will respond to."""
        return (name[3:] for name in dir(self) if name.startswith('do_'))

    def get_help(self, name):
        """Return the documentation string of command having name."""
        try:
            func = getattr(self, 'do_' + name)
        except AttributeError:
            return 'Command not found!'
        doc = inspect.getdoc(func)
        if doc is None:
            return 'Command has no help!'
        return doc

    # These are handler commands.
    # Helps to read documentation strings.

    # noinspection PyUnusedLocal
    @staticmethod
    def do_exit(args):
        """Exit from this area of the server."""
        return EOFError()

    def do_help(self, args):
        """Call help with a command name for more information."""
        if args:
            cmd = 'help' if args[0] == '?' else args[0]
            self.client.print(self.get_help(cmd))
        else:
            self.client.print('Command list:', *self.commands, sep='\n    ')
            self.client.print('Call help with command name for more info.')

    @classmethod
    def load(cls, directory):
        """Generically load static variables from directory."""
        for path in directory.iterdir():
            parts = path.name.split('.')
            if len(parts) == 3:
                kind, static, ext = parts
                if kind == cls.__name__ and static.isupper() and ext == 'dat':
                    new_path = directory / path.name
                    if new_path.is_file():
                        with new_path.open('rb') as file:
                            setattr(cls, static, pickle.load(file))

    @classmethod
    def save(cls, directory):
        """Generically save static variables to directory."""
        for name in filter(str.isupper, dir(cls)):
            path = directory / f'{cls.__name__}.{name}.dat'
            with path.open('wb') as file:
                pickle.dump(getattr(cls, name), file, pickle.HIGHEST_PROTOCOL)
