#! /usr/bin/env python3
"""Provide a Confabulator server implementation with various capabilities.

This server demonstrates some possibilities when implementing a chat host
supporting multiple users, administration controls, named rooms, contacts,
expression interpreters, asynchronous communications, and account options."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '18 December 2017'
__version__ = 1, 0, 2
__all__ = [
    'main',
    'Server'
]

import pathlib
import socket
import sys
import threading
import traceback
import unittest.mock

import server.handlers
import server.handlers.internal
import server.structures


def main(path):
    """Run a chat server using path as root for various files."""
    # Load Static Handler Data
    server.handlers.BanFilter.load(path)
    server.handlers.OutsideMenu.load(path)
    server.handlers.InsideMenu.load(path)
    # Start The Chat Server
    server_thread = Server('', 8989)
    server_thread.start()
    try:
        interruptable_thread_join(server_thread)
    except KeyboardInterrupt:
        run_complete_shutdown(server_thread)
        interruptable_thread_join(server_thread)
    # Wait On Connected Clients
    current = threading.current_thread()
    while True:
        # noinspection PyShadowingNames
        threads = tuple(filter(lambda thread: not (
            thread.daemon or thread is current), threading.enumerate()))
        if not threads:
            break
        try:
            for thread in threads:
                interruptable_thread_join(thread)
        except KeyboardInterrupt:
            run_complete_shutdown(server_thread)
    # Save All Static Data
    server.handlers.InsideMenu.save(path)
    server.handlers.OutsideMenu.save(path)
    server.handlers.BanFilter.save(path)


def interruptable_thread_join(thread):
    """Try to join a thread every tenth of a second until it terminates."""
    while thread.is_alive():
        thread.join(0.1)


def run_complete_shutdown(server_thread):
    """Shutdown the server and force all of the clients to disconnect."""
    print('Complete shutdown in progress ...')
    client = unittest.mock.Mock()
    client.name = 'KeyboardInterrupt'
    client.server = server_thread
    admin_console = server.handlers.internal.AdminConsole(client)
    admin_console.do_shutdown(['all'])


class Server(threading.Thread):
    """Server(host, port) -> Server instance"""

    def __init__(self, host, port):
        """Initialize variables for creating server thread."""
        super().__init__()
        self.clients = []
        self.loop = True
        self.host = host
        self.port = port
        self.data_lock = threading.Lock()

    def run(self):
        """Create and run a server loop for connecting clients."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        while self.loop:
            connection, address = server_socket.accept()
            with self.data_lock:
                if self.loop:
                    client = Client(connection, address)
                    client.server = self
                    self.clients.append(client)
                    Stack(server.handlers.BanFilter(client)).start()
        server_socket.close()


class Client:
    """Client(socket, address) -> Client instance"""

    RECEIVE_SIZE = 1 << 12
    BUFF_SIZE = 1 << 16
    SEPARATOR = b'\r\n'

    def __init__(self, connection, address):
        """Initialize variables that make up a client instance."""
        self.closed = False
        self.socket = connection
        self.address = address
        self.buffer = bytes()

    def receive(self):
        """Return a line having a separator at its end."""
        if self.closed:
            raise SystemExit
        while self.SEPARATOR not in self.buffer:
            try:
                data = self.socket.recv(self.RECEIVE_SIZE)
            except socket.error:
                self.close()
            else:
                if not data or len(self.buffer) + len(data) > self.BUFF_SIZE:
                    self.close()
                self.buffer += data
        index = self.buffer.index(self.SEPARATOR) + len(self.SEPARATOR)
        self.buffer, text = self.buffer[index:], self.buffer[:index]
        return text

    def send(self, text):
        """Normalize and encode text before sending all data."""
        if self.closed:
            raise SystemExit
        for index in range(len(self.SEPARATOR), 0, -1):
            text = text.replace(self.SEPARATOR[:index], self.SEPARATOR[-1:])
        self.socket.sendall(text.replace(self.SEPARATOR[-1:], self.SEPARATOR))

    def close(self, suppress_exit=False):
        """Properly close socket and optionally signal end-of-stream."""
        if self.closed:
            raise SystemExit
        self.closed = True
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
        if not suppress_exit:
            raise SystemExit

    def input(self, *prompt):
        """Print prompt if given and return the decoded line sans separator."""
        if prompt:
            assert len(prompt) == 1, 'One argument at most allowed!'
            self.print(*prompt)
        return self.receive()[:-len(self.SEPARATOR)].decode()

    def print(self, *value, sep=' ', end='\n'):
        """Format arguments and send resulting string to client."""
        self.send(f'{sep.join(map(str, value))}{end}'.encode())


class Stack(threading.Thread):
    """Stack(handler) -> Stack instance"""

    def __init__(self, handler):
        """Initialize stack with client handler."""
        super().__init__()
        self.root = handler
        self.stack = [handler]

    def run(self):
        """Execute dedicated thread for processing client handlers."""
        client = self.root.client
        try:
            while self.stack:
                try:
                    handler = self.stack[-1].handle()
                except SystemExit:
                    raise
                except Exception as error:
                    # noinspection PyPep8,PyBroadException
                    try:
                        client.print('X' * 70)
                        client.print('Please report this error ASAP!')
                        client.print('X' * 70)
                        client.print(traceback.format_exc())
                        client.print('X' * 70)
                    except:
                        pass
                    raise error
                if handler is None:
                    self.stack.pop()
                else:
                    self.stack.append(handler)
        except SystemExit:
            pass
        finally:
            # noinspection PyPep8,PyBroadException
            try:
                with client.server.data_lock:
                    client.server.clients.remove(client)
                client.account.online = False
            except:
                pass


class Account:
    """Account(administrator) -> Account instance"""

    def __init__(self, administrator):
        """Initialize Account with various variables it requires."""
        self.administrator = administrator
        self.data_lock = threading.Lock()
        self.online = False
        self.password = ''
        self.contacts = []
        self.messages = []
        self.forgiven = 0
        self.client = lambda: None

    def __getstate__(self):
        """Return state of account for pickling purposes."""
        state = self.__dict__.copy()
        del state['data_lock']
        del state['online']
        if 'client' in state:
            del state['client']
        return state

    def __setstate__(self, state):
        """Set the state of this instance while unpickling."""
        self.__dict__.update(state)
        self.data_lock = threading.Lock()
        self.online = False

    def add_contact(self, name):
        """Try to add contact name to contact list for this account."""
        with self.data_lock:
            assert name not in self.contacts
            if server.handlers.OutsideMenu.account_exists(name):
                self.contacts.append(name)
                return True
            return False

    def broadcast(self, message):
        """If there is a client for this account, display message."""
        with self.data_lock:
            if self.online:
                # noinspection PyNoneFunctionAssignment
                client = self.client()
                if client is not None:
                    client.print(message)

    # noinspection PyUnusedLocal
    def cleanup(self, weak_reference):
        """Remove the client associated with this account."""
        del self.client

    def delete_message(self, data):
        """Remove the given message(s) from this account."""
        if isinstance(data, (list, tuple)):
            for message in data:
                self.delete_message(message)
        elif isinstance(data, server.structures.Message):
            with self.data_lock:
                if data in self.messages:
                    self.messages.remove(data)
        else:
            raise TypeError('Data type not expected!')

    def force_disconnect(self):
        """If there is a client for this account, disconnect it."""
        with self.data_lock:
            if self.online:
                # noinspection PyNoneFunctionAssignment
                client = self.client()
                if client is not None:
                    client.close(True)

    @staticmethod
    def prune_by_source(source, messages):
        """Remove messages that do not match the required source."""
        return messages if source is None or not messages else tuple(filter(
            lambda message: message.source == source, messages
        ))

    @staticmethod
    def prune_by_status(status, messages):
        """Remove messages that do not match the required status."""
        if status is None or not messages:
            return messages
        assert status in {'read', 'unread'}, 'Status is not valid!'
        return tuple(filter(
            lambda message: message.new == (status == 'unread'), messages
        ))

    def purge_contacts(self):
        """Delete all contact information from this account."""
        with self.data_lock:
            self.contacts = []

    def purge_messages(self):
        """Delete all messages stored on this account."""
        with self.data_lock:
            self.messages = []

    def remove_contact(self, name):
        """Remove contact name from contact list on this account."""
        with self.data_lock:
            if name in self.contacts:
                self.contacts.remove(name)
                return True
            return False

    def show_contacts(self, client, status):
        """Print account contact list to given client."""
        with self.data_lock:
            contacts = list(self.contacts)
        if contacts:
            if status:
                for index, name in enumerate(contacts):
                    filler = ('FF', 'N')[
                        server.handlers.OutsideMenu.is_online(name)]
                    client.print(f'({index + 1}) {name} [O{filler}line]')
            else:
                for index, name in enumerate(contacts):
                    client.print(f'({index + 1}) {name}')
        else:
            client.print('Contact list is empty.')
        return contacts

    def show_message_summary(self, client, status, length, *,
                             filter_status=None, filter_source=None):
        """Print a formatted summary of the messages on this account."""
        with self.data_lock:
            messages = list(self.messages)
        messages = self.prune_by_status(filter_status, messages)
        messages = self.prune_by_source(filter_source, messages)
        if messages:
            filler = ''
            for index, data in enumerate(messages):
                if status:
                    filler = (' [read]', ' [Unread]')[data.new]
                client.print(f'Message {index + 1} '
                             f'from {data.source}{filler}:')
                text = data.message.replace('\n', ' ')
                if len(text) > length:
                    client.print(f'    {text[:length]}...')
                else:
                    client.print(f'    {text}')
        else:
            client.print('There are no messages.')
        return messages


if __name__ == '__main__':
    main(pathlib.Path(sys.argv[0]).parent)
