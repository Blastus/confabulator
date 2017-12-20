#! /usr/bin/env python3
"""Implements much of a server's internal structure.

All of the classes in this module are part of how a server operates internally.
The enum function is a simple tool for creating C-style enumerations and could
be used elsewhere. That is why it is the only name that get exported."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '18 December 2017'
__version__ = 1, 0, 0
__all__ = [
    'enum'
]

import socket
import textwrap
import threading

import server.structures
from . import common
from . import external
from . import plugins


def enum(names):
    """Create a simple enumeration having similarities to C."""
    # noinspection PyTypeChecker
    return type('enum', (), dict(map(reversed, enumerate(
        names.replace(',', ' ').split())), __slots__=()))()


class AdminConsole(common.Handler):
    """AdminConsole(client) -> AdminConsole instance"""

    shutdown = enum('server, users, admin, all')

    def handle(self):
        """Show client status of action and run command loop."""
        self.client.print('Opening admin console ...')
        return self.command_loop()

    # These are additional commands this handler recognizes.

    def do_account(self, args):
        """Access all account related controls."""
        if not args:
            self.client.print('Try view, remove, or edit.')
            return
        command = args[0]
        if command == 'view':
            self.account_view(None)
        elif command == 'remove':
            self.account_remove(args[1:])
        elif command == 'edit':
            return self.account_edit(args[1:])
        else:
            self.client.print('Try view, remove, or edit.')

    def do_ban(self, args):
        """Access all IP ban filter controls."""
        if not args:
            self.client.print('Try view, add, or remove.')
            return
        command = args[0]
        if command == 'view':
            self.ban_view(None)
        elif command == 'add':
            self.ban_add(args[1:])
        elif command == 'remove':
            self.ban_remove(args[1:])
        else:
            self.client.print('Try view, add, or remove.')

    # noinspection PyUnusedLocal
    def do_channels(self, args):
        """View a list of all current channels."""
        names = external.InsideMenu.get_channel_names()
        if names:
            self.client.print(f'Channel{len(names) == 1 and " " or "s "}'
                              f'currently in existence:')
            for name in names:
                self.client.print('   ', name)
        else:
            self.client.print('There are no channels at this time.')

    def do_shutdown(self, args):
        """Arrange for the server to shutdown and save its data."""
        if not args:
            self.client.print('Try server, users, admin, or all.')
            return
        message = self.client.name + ' is shutting down your connection.'
        level = getattr(self.shutdown, args[0], -1)
        if level == self.shutdown.server:
            self.shutdown_server(message)
        elif level > self.shutdown.server:
            self.shutdown_server(message)
            self.disconnect_accounts(message, level)
        else:
            self.client.print('Try server, users, admin, or all.')

    def account_edit(self, args):
        """Return an AccountEditor for the selected account."""
        if args:
            name = args[0]
        else:
            name = self.get_account_name()
        if name is not None:
            if name == self.client.name:
                self.client.print('You may not edit yourself.')
            else:
                with external.OutsideMenu.data_lock:
                    if name in external.OutsideMenu.ACCOUNTS:
                        account = external.OutsideMenu.ACCOUNTS[name]
                    else:
                        self.client.print('Unable to access account.')
                        return
                return AccountEditor(self.client, name, account)

    def account_remove(self, args):
        """Remove account specified by client."""
        if args:
            name = args[0]
            if name == self.client.name:
                self.client.print('You cannot remove yourself.')
                return
            else:
                success = self.disconnect_and_remove(name)
        else:
            name = self.get_account_name()
            if name is None:
                return
            success = self.disconnect_and_remove(name)
        if success:
            self.client.print('Account has been removed.')

    def account_view(self, account_list):
        """Print formatted list of accounts."""
        if account_list is None:
            with external.OutsideMenu.data_lock:
                account_list = list(external.OutsideMenu.ACCOUNTS.keys())
        for index, address in enumerate(account_list):
            self.client.print(f'({index + 1}) {address}')

    def ban_add(self, args):
        """Add an address to the list of those banned."""
        address = args[0] if args else self.client.input('Address:')
        if address:
            address = address.casefold()
            with external.BanFilter.data_lock:
                if address in external.BanFilter.BLOCKED:
                    self.client.print('Address in already in ban list.')
                else:
                    external.BanFilter.BLOCKED.append(address)
                    self.client.print('Address has been successfully added.')
        else:
            self.client.print('Empty address may not be added.')

    def ban_remove(self, args):
        """Remove an address from the list of those banned."""
        if args:
            address = args[0].casefold()
            with external.BanFilter.data_lock:
                if address in external.BanFilter.BLOCKED:
                    external.BanFilter.BLOCKED.remove(address)
                else:
                    self.client.print('Address not found.')
                    return
        else:
            with external.BanFilter.data_lock:
                address_list = list(external.BanFilter.BLOCKED)
            self.ban_view(address_list)
            if address_list:
                # noinspection PyPep8,PyBroadException
                try:
                    index = int(self.client.input('Item number?')) - 1
                    assert 0 <= index < len(address_list)
                except:
                    self.client.print('You must enter a valid number.')
                    return
                else:
                    address = address_list[index]
                    with external.BanFilter.data_lock:
                        while address in external.BanFilter.BLOCKED:
                            external.BanFilter.BLOCKED.remove(address)
        self.client.print('Address has been removed.')

    def ban_view(self, address_list):
        """View list of addresses that are banned."""
        if address_list is None:
            with external.BanFilter.data_lock:
                address_list = list(external.BanFilter.BLOCKED)
        if address_list:
            for index, address in enumerate(address_list):
                self.client.print(f'({index + 1}) {address}')
        else:
            self.client.print('No one is in the ban list.')

    def disconnect_accounts(self, message, level):
        """Send message to matching accounts and disconnect them."""
        with external.OutsideMenu.data_lock:
            accounts = list(external.OutsideMenu.ACCOUNTS.values())
        for account in accounts:
            if account is not self.client.account:
                if level > self.shutdown.users or not account.administrator:
                    account.broadcast(message)
                    account.force_disconnect()
        self.client.print('Shutdown process has been completed.')
        if level == self.shutdown.all:
            self.client.close()

    def disconnect_and_remove(self, name):
        """Force account name to disconnect and then delete."""
        with external.OutsideMenu.data_lock:
            if name in external.OutsideMenu.ACCOUNTS:
                external.OutsideMenu.ACCOUNTS[name].force_disconnect()
            else:
                self.client.print('Account does not exist.')
                return False
        external.OutsideMenu.delete_account(name)
        return True

    def disconnect_clients(self, message, client_array):
        """Send message to client and disconnect them."""
        count = 0
        for client in client_array:
            if not hasattr(client, 'name'):
                client.print(message)
                client.close(True)
                count += 1
        self.client.print(f'{count} sleeper'
                          f'{("s were", " was")[count == 1]} disconnected.')

    def get_account_name(self):
        """Display accounts and get name for one of them."""
        with external.OutsideMenu.data_lock:
            names = external.OutsideMenu.ACCOUNTS.keys()
            names = filter(lambda name: name != self.client.name, names)
            account_list = list(names)
        if account_list:
            self.account_view(account_list)
            # noinspection PyPep8,PyBroadException
            try:
                index = int(self.client.input('Account number?')) - 1
                assert 0 <= index < len(account_list)
            except:
                self.client.print('You must enter a valid number.')
            else:
                return account_list[index]
        else:
            self.client.print('There are no other accounts.')

    def shutdown_server(self, message):
        """Shutdown server to disconnect clients and save static data."""
        server_thread = self.client.server
        with server_thread.data_lock:
            if server_thread.loop:
                server_thread.loop = False
                socket.create_connection(
                    ('localhost', self.client.server.port))
                self.client.print('Server has been shutdown.')
                client_array = tuple(server_thread.clients)
            else:
                self.client.print('Server was already closed.')
                client_array = None
        if client_array is not None:
            self.disconnect_clients(message, client_array)


class AccountEditor(common.Handler):
    """AccountEditor(client, name, account) -> AccountEditor instance"""

    def __init__(self, client, name, account):
        """Initialize the editor with information on the account."""
        super().__init__(client)
        self.name = name
        self.account = account

    def handle(self):
        """Handle all instructions from the client."""
        self.client.print('Opening account editor ...')
        return self.command_loop()

    # These are additional commands this handler recognizes.

    def do_edit(self, args):
        """Change various attributes of the account."""
        attr = args[0] if args else self.client.input('What?')
        account = self.account
        if attr == 'admin':
            with account.data_lock:
                admin = account.administrator = not account.administrator
            self.client.print(f'{self.name} is {("not ", "")[admin]}'
                              f'an administrator now.')
        elif attr == 'password':
            word = args[1] if len(args) > 1 else self.client.input('Password:')
            with account.data_lock:
                account.password = word
            self.client.print('Password has been changed to', repr(word))
        elif attr == 'forgiven':
            if len(args) > 1 and args[1] == 'reset':
                reset = True
            else:
                reset = self.client.input('Reset?') in common.YES_WORDS
            if reset:
                with account.data_lock:
                    account.forgiven = 0
                self.client.print('Forgiven count has been set to zero.')
        else:
            self.client.print('Try admin, password, or forgiven.')

    # noinspection PyUnusedLocal
    def do_info(self, args):
        """Show information about the current account."""
        self.client.print(f'About account "{self.name}":')
        account = self.account
        with account.data_lock:
            self.client.print('Admin    =', account.administrator)
            self.client.print('Online   =', account.online)
            self.client.print('Friends  =', len(account.contacts))
            self.client.print('Messages =', len(account.messages))
            self.client.print('Forgiven =', account.forgiven)

    # noinspection PyUnusedLocal
    def do_password(self, args):
        """Show the password on the account."""
        self.client.print('Username:', repr(self.name))
        with self.account.data_lock:
            self.client.print('Password:', repr(self.account.password))

    def do_read(self, args):
        """Show account's contact list or read message summaries."""
        attr = args[0] if args else self.client.input('Contacts or messages?')
        account = self.account
        if attr == 'contacts':
            self.client.print(f"{self.name}'s contact list:")
            account.show_contacts(self.client, False)
        elif attr == 'messages':
            self.client.print('First 70 bytes of each message:')
            account.show_message_summary(self.client, False, 70)
        else:
            self.client.print('Try contacts or messages.')


class ChannelServer(common.Handler):
    """ChannelServer(channel_name, owner) -> ChannelServer instance"""

    state = enum('start, setup, ready, reset, final')
    builtin_buffer_limit = 10000

    # noinspection PyMissingConstructor
    def __init__(self, channel_name, owner):
        """Initialize the ChannelServer with information about the channel."""
        self.channel_name = channel_name
        self.owner = owner
        self.password = ''
        self.buffer = []
        self.buffer_size = None
        self.replay_size = 10
        self.status = self.state.start
        self.data_lock = threading.Lock()
        self.connected_clients = {}
        self.muted_to_muter = {}
        self.kicked = []
        self.banned = []
        self.admin_lock = threading.Lock()
        self.admin_name = ''

    def __getstate__(self):
        """Get the state of the channel for saving and pickling."""
        state = self.__dict__.copy()
        del state['data_lock']
        del state['admin_lock']
        del state['connected_clients']
        return state

    def __setstate__(self, state):
        """Restore the state of the channel when loading and unpickling."""
        self.__dict__.update(state)
        self.data_lock = threading.Lock()
        self.connected_clients = {}
        self.admin_lock = threading.Lock()

    @staticmethod
    def get_size(client, args=None):
        """Get a number that represents a size."""
        while True:
            if args:
                line, args = args[0], None
            else:
                line = client.input('Size limitation:')
            if line in {'all', 'infinite', 'total'}:
                return
            try:
                size = int(line)
                assert size >= 0
            except (ValueError, AssertionError):
                client.print('Please enter a non-negative number.')
            else:
                return size

    @property
    def client(self):
        """Get the correct client based on the current thread."""
        with self.data_lock:
            return self.connected_clients[threading.current_thread().ident]

    def handle(self):
        """Handle people connecting to the channel server."""
        try:
            handler = self.dispatch()
        finally:
            name = self.client.name
            with self.data_lock:
                while name in self.kicked:
                    self.kicked.remove(name)
            self.disconnect()
        return handler

    # These are additional commands this handler recognizes.

    # noinspection PyUnusedLocal
    def do_admin(self, args):
        """Owner: change this channels settings."""
        if self.privileged():
            return ChannelAdmin(self.client, self)

    def do_ban(self, args):
        """Owner: ban a user from joining this channel."""
        client = self.client
        if self.privileged():
            if not args:
                client.print('Try add, del, or list.')
                return
            command = args[0]
            if command == 'add':
                name = args[1] if len(args) > 1 else client.input('Who?')
                if not name:
                    client.print('Cancelling ...')
                    return
                self.add_ban(client, name)
            elif command == 'del':
                name = args[1] if len(args) > 1 else client.input('Who?')
                if not name:
                    client.print('Cancelling ...')
                    return
                self.del_ban(client, name)
            elif command == 'list':
                self.list_ban(client)
            else:
                client.print('Try add, del, or list.')

    def do_invite(self, args):
        """Invite someone to join this channel."""
        client = self.client
        with self.data_lock:
            exists = self.channel_name is not None
            password = self.password
        if not exists:
            client.print('This channel has been permanently closed.')
            return
        if not password or self.privileged():
            self.send_invitation(args, client)

    def do_kick(self, args, verbose=True):
        """Owner: kick a user off this channel."""
        if self.privileged():
            name = args[0] if args else self.client.input('Who?')
            printer = self.client.print if verbose else lambda *_: None
            if not name:
                printer('Cancelling ...')
                return
            protected = self.is_protected(name)
            if protected is not None:
                if protected:
                    printer(name, 'cannot be kicked.')
                    return
                with self.data_lock:
                    connected = self.connected_clients.items()
                for identity, client in connected:
                    if client.name == name:
                        with self.data_lock:
                            if identity in self.connected_clients:
                                self.kicked.append(name)
                                printer(name, 'has been kicked.')
                                break
                else:
                    printer(name, 'is not on this channel.')

    # noinspection PyUnusedLocal
    def do_list(self, args):
        """Show everyone connected to this channel."""
        with self.data_lock:
            client_list = tuple(self.connected_clients.values())
        if len(client_list) == 1:
            self.client.print('You alone are on this channel.')
        else:
            self.client.print('Current connected to this channel:')
            for client in client_list:
                self.client.print('   ', client.name)

    def do_mute(self, args):
        """Access and change your muted user list."""
        client = self.client
        if not args:
            client.print('Try add, del, or list.')
            return
        command = args[0]
        if command == 'add':
            muted = args[1] if len(args) > 1 else client.input('Who?')
            self.add_mute(muted, client)
        elif command == 'del':
            muted = args[1] if len(args) > 1 else client.input('Who?')
            self.del_mute(muted, client)
        elif command == 'list':
            self.list_mute(client)
        else:
            self.client.print('Try add, del, or list.')

    # noinspection PyUnusedLocal
    def do_summary(self, args):
        """Proof of concept: Mark V Shaney summarizes the channel."""
        with self.data_lock:
            buffer = self.buffer[:]
        if buffer:
            size = (len(buffer) + 3) // 4
            return plugins.MVSHandler(self.client, buffer, size, self)
        else:
            self.client.print('There is nothing to summarize.')

    def do_whisper(self, args):
        """Send a message to one specific person."""
        client = self.client
        name = args[0] if args else client.input('Who?')
        if not name:
            client.print('Cancelling ...')
            return
        if not external.OutsideMenu.account_exists(name):
            client.print(name, 'does not exist.')
            return
        message = client.input('Message:')
        if not message:
            client.print('You may not whisper empty messages.')
            return
        if self.send_whisper(name, message):
            client.print('Message sent.')
        else:
            client.print(name, 'no longer has an account.')

    def add_ban(self, client, name):
        """Try to ban user identified by name."""
        protected = self.is_protected(name)
        if protected is not None:
            if protected:
                client.print(name, 'cannot be banned.')
            else:
                with self.data_lock:
                    will_ban = name not in self.banned
                    if will_ban:
                        self.banned.append(name)
                if will_ban:
                    self.do_kick([name], False)
                    client.print(name, 'has been banned.')
                else:
                    client.print(name, 'was already been banned.')

    def add_line(self, name, line):
        """Add a line to the channel buffer."""
        with self.data_lock:
            if self.buffer_size is None:
                buffer_size = self.builtin_buffer_limit
            else:
                buffer_size = min(self.buffer_size, self.builtin_buffer_limit)
            channel_line = server.structures.ChannelLine(name, line)
            if buffer_size:
                self.buffer.append(channel_line)
                if len(self.buffer) > buffer_size:
                    del self.buffer[:len(self.buffer) - buffer_size]
            return channel_line

    def add_mute(self, muted, client):
        """Add someone to list of muted people."""
        with self.data_lock:
            okay = external.OutsideMenu.account_exists(muted)
            if okay:
                if muted in self.muted_to_muter:
                    muting_clients = self.muted_to_muter[muted]
                    if client.name not in muting_clients:
                        muting_clients.append(client.name)
                        okay += 1
                else:
                    self.muted_to_muter[muted] = [client.name]
                    okay += 1
        if okay:
            if okay > 1:
                client.print(muted, 'has been muted.')
            else:
                client.print(muted, 'was already muted.')
        else:
            if muted:
                client.print(muted, 'does not exist.')
            else:
                client.print('Cancelling ...')

    def authenticate(self):
        """Allow client to authenticate to the channel if needed."""
        with self.data_lock:
            password = self.password
        if not password or self.privileged(False):
            return True
        return self.client.input('Password to connect:') == password

    def broadcast(self, channel_line, echo):
        """Send message to all connected clients except the sender."""
        client = self.client
        with self.data_lock:
            clients = tuple(self.connected_clients.values())
            muter = self.muted_to_muter.get(channel_line.source, [])
            kicked = tuple(self.kicked)

        # noinspection PyShadowingNames
        def accept(destination):
            if destination.name in kicked:
                return False
            if destination.name in muter:
                return False
            if echo:
                return True
            return destination is not client

        for destination in filter(accept, clients):
            channel_line.echo(destination)

    def connect(self, client):
        """Connect the client to this channel."""
        with self.data_lock:
            self.connected_clients[threading.current_thread().ident] = client
        return self

    def del_ban(self, client, name):
        """Try to remove a ban from user identified by name."""
        with self.data_lock:
            will_remove = name in self.banned
            if will_remove:
                self.banned.remove(name)
        if will_remove:
            client.print(name, 'is no longer banned on this channel.')
        else:
            client.print(name, 'was not banned on this channel.')
        return False

    def del_mute(self, muted, client):
        """Remove someone from list of muted people."""
        if muted:
            message = muted + ' was not muted.'
            with self.data_lock:
                if muted in self.muted_to_muter:
                    muting_clients = self.muted_to_muter[muted]
                    if client.name in muting_clients:
                        message = muted + ' is no longer muted.'
                        muting_clients.remove(client.name)
                        if not muting_clients:
                            del self.muted_to_muter[muted]
            client.print(message)
        else:
            client.print('Cancelling ...')

    def disconnect(self):
        """Remove the client from this channel's registry."""
        with self.data_lock:
            del self.connected_clients[threading.current_thread().ident]

    def dispatch(self):
        """Ensure the channel is setup before allow people to enter."""
        client = self.client
        with self.data_lock:
            if self.status == self.state.final:
                return
            if self.status == self.state.reset and client.name == self.owner:
                self.status = self.state.start
            status = self.status
            if self.status == self.state.start:
                self.status = self.state.setup
        if status == self.state.start:
            try:
                self.setup_channel()
            finally:
                with self.data_lock:
                    status = self.status = self.state.ready
        if status in {self.state.setup, self.state.reset}:
            client.print(self.owner, 'is setting up this channel.')
            return
        elif status == self.state.ready:
            return self.run_channel()
        else:
            raise ValueError(str(status) + ' is not a proper status value!')

    def is_protected(self, name):
        """Find out if user identified by name has certain protections."""
        with self.data_lock:
            if self.owner == name:
                return True
        administrator = external.OutsideMenu.is_administrator(name)
        if administrator is None:
            self.client.print(name, 'does not exist.')
        else:
            return administrator

    def list_ban(self, client):
        """List the names of users banned on this channel."""
        with self.data_lock:
            banned = tuple(self.banned)
        if banned:
            client.print('Those that are banned from this channel:')
            for name in banned:
                client.print('   ', name)
        else:
            client.print('No one has been banned on this channel.')

    def list_mute(self, client):
        """List people who have been muted."""
        with self.data_lock:
            m2m = self.muted_to_muter.copy()
        you_mute = []
        for muted in m2m:
            if client.name in m2m[muted]:
                you_mute.append(muted)
        if you_mute:
            client.print('You have muted:', *you_mute, sep='\n    ')
        else:
            client.print('Your list is empty.')

    def may_whisper(self, name):
        """Find out if client may whisper to user identified by name."""
        sender = self.client.name
        with self.data_lock:
            if name in self.muted_to_muter.get(sender, ()):
                return
            clients = self.connected_clients.values()
        for client in clients:
            if client.name == name:
                return client

    def message_loop(self):
        """Process incoming commands from client."""
        client = self.client
        event = server.structures.ChannelLine('EVENT',
                                              client.name + ' is joining.')
        self.broadcast(event, False)
        while True:
            line = client.input()
            with self.data_lock:
                if client.name in self.kicked:
                    client.print('You have been kicked out of this channel.')
                    return
            if line.startswith(':'):
                value = self.run_command(line[1:])
                if value == '__json_help__':
                    pass
                elif isinstance(value, AttributeError):
                    client.print('Command not found!')
                elif isinstance(value, EOFError):
                    return
                elif value is not None:
                    return value
            else:
                channel_line = self.add_line(client.name, line)
                self.broadcast(channel_line, True)

    def privileged(self, show_error=True):
        """Check if current user is privileged and display error if needed."""
        client = self.client
        with client.account.data_lock:
            if client.account.administrator:
                return True
        with self.data_lock:
            if client.name == self.owner:
                return True
        if show_error:
            client.print('Only administrators or channel owner may do that.')

    def run_channel(self):
        """Handle user entering channel and run message loop as needed."""
        client = self.client
        with self.data_lock:
            banned = client.name in self.banned
        if banned:
            client.print('You have been banned from this channel.')
        elif self.authenticate():
            self.replay_buffer()
            self.show_status()
            try:
                data = self.message_loop()
            finally:
                event = server.structures.ChannelLine(
                    'EVENT', self.client.name + ' is leaving.'
                )
                self.broadcast(event, False)
            return data
        else:
            client.print('You have failed authentication.')

    def replay_buffer(self):
        """Show the message buffer to client."""
        with self.data_lock:
            if self.replay_size is None:
                buffer = tuple(self.buffer)
            elif self.replay_size > 0:
                buffer = tuple(self.buffer[-self.replay_size:])
            else:
                buffer = ()
        client = self.client
        for line in buffer:
            line.echo(client)

    def send_invitation(self, args, client):
        """Send an invitation to another users to join this channel."""
        name = args[0] if args else client.input('Who?')
        if name:
            if name == client.name:
                client.print('You are already here.')
                return
            with self.data_lock:
                channel_name = self.channel_name
            if channel_name is None:
                client.print('This channel has been permanently closed.')
                return
            message = f'{client.name} has invited you to channel ' \
                      f'{channel_name}.'
            if self.password:
                message += '\n\nUse this to get in: ' + repr(self.password)
            if external.OutsideMenu.deliver_message(client.name, name,
                                                    message):
                client.print('Invitation has been sent.')
            else:
                client.print(name, 'does not exist.')
        else:
            client.print('Cancelling ...')

    def send_whisper(self, name, message):
        """Send a whispered message to user identified by name."""
        client = self.may_whisper(name)
        if client is None:
            return external.OutsideMenu.deliver_message(self.client.name, name,
                                                        message)
        client.print(f'({self.client.name}) {message}')
        return True

    def show_status(self):
        """Show how many people are connected to the channel."""
        with self.data_lock:
            connected = len(self.connected_clients)
        self.client.print(f'{connected} '
                          f'{("people are", "person is")[connected == 1]} '
                          f'connected.')

    def setup_buffer_size(self):
        """Allow the client to set the buffer size."""
        client = self.client
        answer = client.input('Do you want to set the buffer size?')
        if answer in common.YES_WORDS:
            size = self.get_size(client)
            with self.data_lock:
                self.buffer_size = size

    def setup_channel(self):
        """Allow client to setup the channel (password, buffer, and replay)."""
        self.setup_password()
        self.setup_buffer_size()
        self.setup_replay_size()

    def setup_password(self):
        """Allow client to set the password."""
        answer = self.client.input('Password protect this channel?')
        if answer in common.YES_WORDS:
            while True:
                password = self.client.input('Set password to:')
                if password:
                    with self.data_lock:
                        self.password = password
                    return
                else:
                    self.client.print('Password may not be empty.')

    def setup_replay_size(self):
        """Allow the client to set the replay size."""
        client = self.client
        answer = client.input('Do you want to set the replay size?')
        if answer in common.YES_WORDS:
            size = self.get_size(client)
            with self.data_lock:
                self.replay_size = size

    # The following commands will never be created using the current
    # framework this program is built upon. They are here to reflect
    # what may happen in the future, dreams of greater expectations.

    # noinspection PyUnusedLocal
    def do_bot(self, args):
        """Owner: add optional channel commands."""
        if self.privileged():
            self.client.print('Reserved command for future expansion ...')
            # this would be a good place for the math expression evaluator

    # noinspection PyUnusedLocal
    def do_map(self, args):
        """Owner: add optional channel modifiers."""
        if self.privileged():
            self.client.print('Reserved command for future expansion ...')
            # scrambling the middle letters of all words would be very fun

    # noinspection PyUnusedLocal
    def do_run(self, args):
        """Owner: add optional channel extensions."""
        if self.privileged():
            self.client.print('Reserved command for future expansion ...')
            # alternate programs could be implemented and executed via run


class ChannelAdmin(common.Handler):
    """ChannelAdmin(client, channel) -> ChannelAdmin instance"""

    def __init__(self, client, channel):
        """Initialize admin console with client and associated channel."""
        super().__init__(client)
        self.channel = channel

    def handle(self):
        """Acquire control of the channel and run the command loop."""
        admin = self.channel.admin_lock.acquire(False)
        if admin:
            with self.channel.data_lock:
                self.channel.admin_name = self.client.name
            try:
                self.client.print('Opening admin console ...')
                handler = self.command_loop()
            finally:
                self.channel.admin_lock.release()
            if handler is None:
                self.channel.connect(self.client)
            return handler
        else:
            self.client.print(self.channel.admin_name,
                              'is currently using the admin console.')
            self.channel.connect(self.client)

    # These are additional commands this handler recognizes.

    def do_buffer(self, args):
        """Set the buffer size of this channel."""
        size = ChannelServer.get_size(self.client, args)
        with self.channel.data_lock:
            self.channel.buffer_size = size

    # noinspection PyUnusedLocal
    def do_close(self, args):
        """Kick everyone off the channel (useful after delete)."""
        with self.channel.data_lock:
            for client in self.channel.connected_clients.values():
                self.channel.kicked.append(client.name)
        self.client.print('Everyone has been kicked off the channel.')

    # noinspection PyUnusedLocal
    def do_delete(self, args):
        """Un-register this channel as though it did not exist."""
        with self.channel.data_lock:
            deleted = self.channel.channel_name is None
            if not deleted:
                assert external.InsideMenu.delete_channel(
                    self.channel.channel_name), \
                    'Name was set, but it was not registered.'
                self.channel.channel_name = None
        if deleted:
            self.client.print('This channel had been previously deleted.')
        else:
            self.client.print('This channel is no longer enabled.')

    # noinspection PyUnusedLocal
    def do_finalize(self, args):
        """Delete, close, and reset the channel (returns you to main menu)."""
        with self.channel.data_lock:
            self.channel.status = ChannelServer.state.final
            if self.channel.channel_name is not None:
                external.InsideMenu.delete_channel(self.channel.channel_name)
                self.channel.channel_name = None
            for client in self.channel.connected_clients.values():
                self.channel.kicked.append(client.name)
            self.reset_channel()
        self.client.print('The channel has been finalized.')
        self.client.print('Returning to the main menu ...')
        return EOFError()

    # noinspection PyUnusedLocal
    def do_history(self, args):
        """Show the entire contents of the channel buffer."""
        with self.channel.data_lock:
            buffer = tuple(self.channel.buffer)
        if buffer:
            for line in buffer:
                line.echo(self.client)
        else:
            self.client.print('The channel buffer is empty.')

    def do_owner(self, args):
        """Change the owner of this channel."""
        new_owner = args[0] if args else self.client.input('New owner:')
        if not new_owner:
            self.client.print('Cancelling ...')
            return
        if len(args) > 1 or len(new_owner.split()) > 1:
            self.client.print('Username may not have whitespace!')
            return
        user_exists = False
        with self.channel.data_lock:
            different = new_owner != self.channel.owner
            if different:
                user_exists = external.OutsideMenu.account_exists(new_owner)
                if user_exists:
                    self.channel.owner = new_owner
        if not different:
            self.client.print(new_owner, 'already owns this channel.')
        elif user_exists:
            self.client.print(new_owner, 'is now the owner of this channel.')
        else:
            self.client.print(new_owner, 'does not have an account.')

    def do_password(self, args):
        """Change the password of this channel."""
        if not args:
            self.client.print('Try set or unset.')
            return
        command = args[0]
        if command == 'set':
            word = args[1] if len(args) > 1 else self.client.input('Password:')
            if word:
                with self.channel.data_lock:
                    self.channel.password = word
                self.client.print('Password has been set to:', word)
            else:
                self.client.print('Password may not be empty.')
        elif command == 'unset':
            with self.channel.data_lock:
                self.channel.password = ''
            self.client.print('The password has been cleared.')
        else:
            self.client.print('Try set or unset.')

    # noinspection PyUnusedLocal
    def do_purge(self, args):
        """Clear the contents of the channel buffer."""
        with self.channel.data_lock:
            self.channel.buffer = []
        self.client.print('The buffer has been cleared.')

    def do_rename(self, args):
        """Give this channel a new name not used by another channel."""
        with self.channel.data_lock:
            old_name = self.channel.channel_name
        if old_name is None:
            self.client.print('Deleted channels cannot be renamed.')
            return
        new_name = args[0] if args else self.client.input('New name:')
        if not new_name:
            self.client.print('Cancelling ...')
            return
        if len(args) > 1 or len(new_name.split()) > 1:
            self.client.print('Channel name may not have whitespace!')
            return
        exists, success = self.try_rename(new_name)
        self.show_rename_result(exists, success, new_name)

    def do_replay(self, args):
        """Set the replay size of this channel."""
        size = ChannelServer.get_size(self.client, args)
        with self.channel.data_lock:
            self.channel.replay_size = size

    # noinspection PyUnusedLocal
    def do_reset(self, args):
        """Make the channel like new again with nothing in it."""
        with self.channel.data_lock:
            self.channel.status = ChannelServer.state.reset
            for client in self.channel.connected_clients.values():
                self.channel.kicked.append(client.name)
            self.reset_channel()
        self.client.print('Channel has been reset, and you are its owner.')

    # noinspection PyUnusedLocal
    def do_settings(self, args):
        """Show channel owner, password, buffer size, and replay size."""
        with self.channel.data_lock:
            owner = self.channel.owner
            password = self.channel.password
            buffer_size = self.channel.buffer_size
            replay_size = self.channel.replay_size
        self.client.print('Owner:      ', owner)
        self.client.print('Password:   ', password)
        size = 'Infinite' if buffer_size is None else buffer_size
        self.client.print('Buffer size:', size)
        size = 'Infinite' if replay_size is None else replay_size
        self.client.print('Replay size:', size)

    def reset_channel(self):
        """Restore the channel to a new-like condition."""
        self.channel.owner = self.client.name
        self.channel.password = ''
        self.channel.buffer = []
        self.channel.buffer_size = None
        self.channel.replay_size = 10
        self.channel.muted_to_muter = {}
        self.channel.banned = []

    def show_rename_result(self, exists, success, new_name):
        """Show the results of an attempted rename operation."""
        if not exists:
            self.client.print('This channel has been deleted.')
            return
        assert success is not None, 'Name was set, but it was not registered.'
        if success:
            self.client.print(new_name, 'is the new name of this channel.')
        else:
            self.client.print('The name', new_name, 'is already in use.')

    def try_rename(self, new_name):
        """Try to rename the channel to a new name."""
        success = None
        with self.channel.data_lock:
            old_name = self.channel.channel_name
            exists = old_name is not None
            if exists:
                success = external.InsideMenu.rename_channel(old_name,
                                                             new_name)
                if success:
                    self.channel.channel_name = new_name
        return exists, success


class ContactManager(common.Handler):
    """ContactManager(client) -> ContactManager instance"""

    def handle(self):
        """Show client status of action and run command loop."""
        self.client.print('Opening contact manager ...')
        return self.command_loop()

    # These are additional commands this handler recognizes.

    def do_add(self, args):
        """Add a friend to your contact list."""
        name = args[0] if args else self.client.input('Who?')
        try:
            status = self.client.account.add_contact(name)
        except AssertionError:
            self.client.print(name, 'is already in your contact list.')
        else:
            if status:
                self.client.print(name, 'has been added to your contact list.')
            else:
                self.client.print(name, 'does not currently exist.')

    def do_remove(self, args):
        """Remove someone from your contact list."""
        name = args[0] if args else self.client.input('Who?')
        if self.client.account.remove_contact(name):
            self.client.print(name, 'has been removed from your contact list.')
        else:
            self.client.print(name, 'is not in your contact list.')

    # noinspection PyUnusedLocal
    def do_show(self, args):
        """Display your friend list with online/offline status."""
        self.client.account.show_contacts(self.client, True)


class MessageManager(common.Handler):
    """MessageManager(client) -> MessageManager instance"""

    def handle(self):
        """Show client status of action and run command loop."""
        self.client.print('Opening message manager ...')
        return self.command_loop()

    # These are additional commands this handler recognizes.

    def do_delete(self, args):
        """Provides various options for deleting your messages."""
        data = self.parse_args(args, True)
        if data is not None:
            self.client.account.delete_message(data)
            self.client.print('Deletion has been completed.')

    def do_read(self, args):
        """Allows you to read a message in its entirety."""
        data = self.parse_args(args, False)
        if data is not None:
            data.new = False
            self.client.print('From:', data.source)
            self.client.print('=' * 70)
            paragraphs = data.message.split('\n\n')
            for index, section in enumerate(paragraphs):
                for line in textwrap.wrap(section.replace('\n', ' ')):
                    self.client.print(line)
                if index + 1 < len(paragraphs):
                    self.client.print()
            self.client.print('=' * 70)

    def do_send(self, args):
        """Allows you to send a message to someone else."""
        name = args[0] if args else self.client.input('Destination:')
        if name == self.client.name:
            self.client.print('You are not allowed to talk to yourself.')
            return
        if not external.OutsideMenu.account_exists(name):
            self.client.print('Account does not exist.')
            return
        text = self.get_message()
        if not text:
            self.client.print('Empty messages may not be sent.')
            return
        if external.OutsideMenu.deliver_message(self.client.name, name, text):
            self.client.print('Message has been delivered.')
        else:
            self.client.print(name, 'was removed while you were writing.')

    # noinspection PyUnusedLocal
    def do_show(self, args, internal=False):
        """Shows messages summaries with status information."""
        data = self.client.account.show_message_summary(self.client, True, 70)
        if internal:
            return data

    def find_message(self, args, allow_all):
        """Find a message that the client has requested."""
        clue = args[0]
        try:
            index = int(clue) - 1
        except ValueError:
            show = self.client.account.show_message_summary
            if clue in {'read', 'unread'}:
                messages = show(self.client, True, 70, filter_status=clue)
            else:
                messages = show(self.client, True, 70, filter_source=clue)
            return self.pick_message(messages, allow_all)
        else:
            with self.client.account.data_lock:
                messages = tuple(self.client.account.messages)
            if 0 <= index < len(messages):
                return messages[index]
            self.client.print('That is not a valid message number.')

    def get_message(self):
        """Get message to send from the client."""
        lines = []
        self.client.print('Please compose your message.')
        self.client.print('Enter 2 blank lines to send.')
        self.client.print('=' * 70)
        while lines[-2:] != ['', '']:
            lines.append(self.client.input())
        self.client.print('=' * 70)
        while lines and not lines[0]:
            del lines[0]
        return '\n'.join(lines[:-2])

    def parse_args(self, args, allow_all):
        """Parse the arguments, show messages, and pick them."""
        if args:
            return self.find_message(args, allow_all)
        messages = self.do_show(args, True)
        return self.pick_message(messages, allow_all)

    def pick_message(self, messages, allow_all):
        """Pick a message the client wants."""
        while messages:
            line = self.client.input('Which one?')
            if not line:
                self.client.print('Cancelling ...')
                break
            if allow_all and line == 'all':
                return messages
            try:
                index = int(line) - 1
                assert 0 <= index < len(messages)
            except (ValueError, AssertionError):
                self.client.print('Please enter a valid message number.')
            else:
                return messages[index]


class AccountOptions(common.Handler):
    """AccountOptions(client) -> AccountOptions instance"""

    def handle(self):
        """Show client status of action and run command loop."""
        self.client.print('Opening account options ...')
        return self.command_loop()

    # These are additional commands this handler recognizes.

    def do_delete_account(self, args):
        """Delete your account permanently."""
        if args and args[0] == 'force':
            delete = True
        else:
            delete = self.client.input('Seriously?') in common.YES_WORDS
        if delete:
            self.client.print('Your account and connection are being closed.')
            external.OutsideMenu.delete_account(self.client.name)
            self.client.close()
        self.client.print('Cancelling ...')

    def do_password(self, args):
        """Change your password."""
        old = args[0] if args else self.client.input('Old password:')
        account = self.client.account
        with account.data_lock:
            if account.password != old:
                self.client.print('Old password is not correct.')
                return
        new = args[1] if len(args) > 1 else self.client.input('New password:')
        if new:
            with account.data_lock:
                account.password = new
            self.client.print('Your password has been changed.')
        else:
            self.client.print('Your password may not be empty.')

    def do_purge(self, args):
        """Purge your messages, contacts, or both."""
        command = args[0] if args else self.client.input('What?')
        if command == 'messages':
            self.client.account.purge_messages()
            self.client.print('All of your messages have been deleted.')
        elif command == 'contacts':
            self.client.account.purge_contacts()
            self.client.print('All of your contacts have been deleted.')
        elif command == 'both':
            self.client.account.purge_messages()
            self.client.account.purge_contacts()
            self.client.print('Your messages and contacts have been deleted.')
        else:
            self.client.print('Try messages, contacts, or both.')
