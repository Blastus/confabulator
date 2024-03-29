#! /usr/bin/env python3
"""Contains the handlers that are needed for immediate use in the server.

The primary reason the classes in this module are needed is for loading and
saving static variables that store all of the server's data. The main function
of the server interacts with these handlers directly for data persistence."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '21 December 2017'
__version__ = 1, 0, 2
__all__ = [
    'BanFilter',
    'OutsideMenu',
    'InsideMenu',
]

import inspect
import socket
import threading
import weakref

import server.complex_server
import server.structures
from . import common
from . import internal
from . import math_engine_1
from . import math_engine_2


class BanFilter(common.Handler):
    """BanFilter(client) -> BanFilter instance"""

    def __init__(self, client):
        """Initialize filter with the client to screen."""
        super().__init__(client)
        self.passed = False

    def handle(self):
        """Verify if client is allowed to continue to OutsideMenu."""
        if self.passed:
            self.client.print('Disconnecting ...')
            self.client.close()
            return
        ip_address = socket.gethostbyname(self.client.address[0])
        if self.client.database.ban_filter_is_banned(ip_address):
            self.client.close()
        self.passed = True
        return OutsideMenu(self.client)

    @staticmethod
    def ban_client(client):
        """Conveniently ban a client using its connection to the database."""
        ip_address = socket.gethostbyname(client.address[0])
        client.database.ban_filter_add(ip_address)


class OutsideMenu(common.Handler):
    """OutsideMenu(client) -> OutsideMenu instance"""

    ACCOUNTS = {}
    data_lock = threading.Lock()
    server_code = None

    @classmethod
    def account_exists(cls, name):
        """Find out if an account with name exists."""
        with cls.data_lock:
            return name in cls.ACCOUNTS

    @staticmethod
    def clean_name_from_channels(name):
        """Remove all references to name in channels."""
        for channel in InsideMenu.get_channels():
            with channel.data_lock:
                if name in channel.muted_to_muter:
                    del channel.muted_to_muter[name]
                while name in channel.banned:
                    channel.banned.remove(name)
                for muted in channel.muted_to_muter.keys():
                    muter = channel.muted_to_muter[muted]
                    if name in muter:
                        muter.remove(name)
                        if not muter:
                            del channel.muted_to_muter[muted]

    @classmethod
    def delete_account(cls, name):
        """Delete the account identified by name."""
        with cls.data_lock:
            if name in cls.ACCOUNTS:
                del cls.ACCOUNTS[name]
                for account in cls.ACCOUNTS.values():
                    with account.data_lock:
                        if name in account.contacts:
                            account.contacts.remove(name)
        cls.clean_name_from_channels(name)

    @classmethod
    def deliver_message(cls, source, name, text):
        """Send message to name via source with text if possible."""
        with cls.data_lock:
            if name in cls.ACCOUNTS:
                account = cls.ACCOUNTS[name]
                with account.data_lock:
                    account.messages.append(
                        server.structures.Message(source, text))
                event = f'[EVENT] {source} has sent you a message.'
                account.broadcast(event)
                return True
            else:
                return False

    @classmethod
    def is_administrator(cls, name):
        """Check if account identified by name is an administrator."""
        with cls.data_lock:
            if name in cls.ACCOUNTS:
                return cls.ACCOUNTS[name].administrator

    @classmethod
    def is_online(cls, name):
        """Check if user identified by name is online."""
        with cls.data_lock:
            if name in cls.ACCOUNTS:
                return cls.ACCOUNTS[name].online
            else:
                return False

    def handle(self):
        """Print banner before entering the command loop."""
        self.print_banner()
        return self.command_loop()

    def print_banner(self):
        """Show banner to the client."""
        #         self.client.print('''\
        # ===================================
        # Welcome to Confabulator
        # Python Edition 1.1
        # ===================================''')
        self.client.print('''\
/----------------------------\\
|                            |
|   Welcome to Confabulator  |
|   ======================   |
|     Python Edition 1.1     |
|                            |
\\----------------------------/''')

    # These are additional commands this handler recognizes.

    def do_login(self, args):
        """Login to the server to access account."""
        name = args[0] if len(args) > 0 else self.client.input('Username:')
        word = args[1] if len(args) > 1 else self.client.input('Password:')
        cls = type(self)
        with self.data_lock:
            if name in cls.ACCOUNTS and \
                            word == cls.ACCOUNTS[name].password:
                account = cls.ACCOUNTS[name]
                with account.data_lock:
                    if account.online:
                        self.client.print('Account is already logged in!')
                        return
                    return self.login_account(account, name)
        self.client.print('Authentication failed!')

    def do_open_source(self, args):
        """Display the entire source code for this program."""
        if args and args[0] == 'force' or \
                self.client.input('Are you sure?') in common.YES_WORDS:
            self.prepare_server_code()
            for line in self.server_code:
                self.client.print(line)

    @classmethod
    def prepare_server_code(cls):
        """Fills a static variable with the project's complete source code."""
        if cls.server_code is None:
            import server.timeout
            import server.handlers
            # noinspection PyUnresolvedReferences
            from . import external
            from . import plugins
            source = []
            for code in (
                server.complex_server,
                server.structures,
                server.timeout,
                server.handlers,
                common,
                external,
                internal,
                math_engine_1,
                math_engine_2,
                plugins
            ):
                path = inspect.getsourcefile(code)
                source.extend((f'# {"=" * len(path)}', f'# {path}'))
                with open(path, 'rt') as file:
                    source.extend(file.read().splitlines())
            cls.server_code = tuple(source)

    def do_register(self, args):
        """Register for an account using this command."""
        if not self.check_terms_of_service():
            return EOFError()
        name = args[0] if args else self.client.input('Username:')
        if len(name.split()) > 1:
            self.client.print('Username may not have whitespace!')
            return
        cls = type(self)
        with self.data_lock:
            if name in cls.ACCOUNTS:
                self.client.print('Account already exists!')
                return
            account = cls.ACCOUNTS[name] = server.complex_server.Account(
                not bool(cls.ACCOUNTS))
        word = args[1] if len(args) > 1 else self.client.input('Password:')
        if len(word.split()) == 1:
            with account.data_lock:
                account.password = word
                return self.login_account(account, name)
        else:
            with self.data_lock:
                del cls.ACCOUNTS[name]
            self.client.print('Password may not have whitespace!')

    def check_terms_of_service(self):
        """Find out if client agrees to these terms of service."""
        #         self.client.print('''\
        # ===================================
        # TERMS OF SERVICE
        #
        # By registering with this service,
        # you agree to be bound by these
        # principle requirements until death
        # or the end of the world:
        #
        # 1. This service is being provided
        # to you for free and must remain
        # free for these terms to continue.
        #
        # 2. Administrators should be held
        # faultless in all they do except
        # promoting falsehood and deception.
        #
        # 3. The account given you will
        # remain the property of the issuer
        # and may be removed without warning.
        #
        # 4. You give up all legal rights,
        # privacy of data, and demands for
        # fairness while using this system.
        #
        # 5. Your terms of service will
        # remain in effect if you lose
        # possession over an account you
        # received.
        # ===================================''')
        self.client.print('''\
/----------------------------\\
|      TERMS OF SERVICE      |
|  ========================  |
|  By registering with this  |
|  service, you agree to be  |
|  bound by these principle  |
|  requirements until death  |
|  or the end of the world:  |
|                            |
|  1. This service is being  |
|  provided to you for free  |
|  and must remain free for  |
|  these terms to continue.  |
|                            |
|  2. Administrators should  |
|  be held faultless in all  |
|  they do except promoting  |
|  falsehood and deception.  |
|                            |
|  3. The account given you  |
|  will remain the property  |
|  of the issuer and may be  |
|  removed without warning.  |
|                            |
|  4. You give up all legal  |
|  rights, privacy of data,  |
|  and demands for fairness  |
|  while using this system.  |
|                            |
|  5. Your terms of service  |
|  will remain in effect if  |
|  you lose possession over  |
|  an account you received.  |
\\----------------------------/''')
        return self.client.input('Do you agree?') in common.YES_WORDS

    def login_account(self, account, name):
        """Complete the action of logging the client into his/her account."""
        account.online = True
        self.client.name = name
        self.client.account = account
        account.client = weakref.ref(self.client, account.cleanup)
        return InsideMenu(self.client)


class InsideMenu(common.Handler):
    """InsideMenu(client) -> InsideMenu instance"""

    data_lock = threading.Lock()
    NEXT_CHANNEL = 1
    CHANNEL_NAMES = {}

    @classmethod
    def channel_exists(cls, name):
        """Find out if channel identified by name exists."""
        with cls.data_lock:
            return name in cls.CHANNEL_NAMES

    @classmethod
    def delete_channel(cls, name):
        """Delete channel name from registry."""
        with cls.data_lock:
            if name in cls.CHANNEL_NAMES:
                # The file cannot be deleted, so leave its history alive.
                # delattr(cls, 'CHANNEL_' + str(cls.CHANNEL_NAMES[name]))
                del cls.CHANNEL_NAMES[name]
                return True
            return False

    @classmethod
    def get_channels(cls):
        """Get a list of real channel (server) objects."""
        with cls.data_lock:
            names = cls.CHANNEL_NAMES.values()
        channels = []
        sentinel = object()
        for index in names:
            channel = getattr(cls, f'CHANNEL_{index}', sentinel)
            if channel is not sentinel:
                channels.append(channel)
        return channels

    @classmethod
    def get_channel_names(cls):
        """Get a list of the channel names."""
        with cls.data_lock:
            return tuple(cls.CHANNEL_NAMES.keys())

    @classmethod
    def rename_channel(cls, old_name, new_name):
        """Change channel's name from old_name to new_name."""
        with cls.data_lock:
            if old_name in cls.CHANNEL_NAMES:
                if new_name in cls.CHANNEL_NAMES:
                    return False
                index = cls.CHANNEL_NAMES[old_name]
                del cls.CHANNEL_NAMES[old_name]
                cls.CHANNEL_NAMES[new_name] = index
                return True

    def handle(self):
        """Handle commands from the client for the inside menu."""
        self.print_status()
        handler = self.command_loop()
        if handler is None:
            with self.client.account.data_lock:
                self.client.account.online = False
                del self.client.account
                del self.client.name
        return handler

    def print_status(self):
        """Show a status message to those just entering the inside menu."""
        if self.client.account.administrator:
            self.client.print('Welcome, administrator!')
        with self.client.account.data_lock:
            new = sum(map(
                lambda message: message.new, self.client.account.messages
            ))
            contacts = list(self.client.account.contacts)
        self.client.print(f'You have {new} new message{("s", "")[new == 1]}.')
        # TODO: The rest of this method needs to be replaced with a call to
        #       db_api.DatabaseManager.user_contact_get_contact_counts
        online = 0
        with OutsideMenu.data_lock:
            for name in contacts:
                if name in OutsideMenu.ACCOUNTS:
                    account = OutsideMenu.ACCOUNTS[name]
                    with account.data_lock:
                        if account.online:
                            online += 1
        total = len(contacts)
        self.client.print(f'{online} of your '
                          f'{total} friend'
                          f'{("s", "")[total == 1]} '
                          f'{("are", "is")[online == 1]} online.')

    # These are additional commands this handler recognizes.

    # noinspection PyUnusedLocal
    def do_admin(self, args):
        """Access the administration console (if you are an administrator)."""
        client = self.client
        if not client.account.administrator:
            cls = type(self)
            key = 'InsideMenu.mercy_limit'
            mercy_limit = client.database.global_setting[key]
            if client.account.forgiven >= mercy_limit:
                BanFilter.ban_client(client)
                OutsideMenu.delete_account(client.name)
                client.print('You have been warned for the last time!')
                client.print('Now your IP address has been blocked &')
                client.print('your account has been completely removed.')
                client.close()
            with client.account.data_lock:
                client.account.forgiven += 1
            client.print('You are not authorized to be here.')
            return EOFError()
        return internal.AdminConsole(client)

    def do_channel(self, args):
        """Allows you create and connect to message channels."""
        name = args[0] if args else self.client.input('Channel to open?')
        if len(args) > 1 or len(name.split()) > 1:
            self.client.print('Channel name may not have whitespace!')
            return
        if name:
            cls = type(self)
            with self.data_lock:
                if name in self.CHANNEL_NAMES:
                    index = str(self.CHANNEL_NAMES[name])
                    channel = getattr(cls, 'CHANNEL_' + index)
                else:
                    channel = internal.ChannelServer(name, self.client.name)
                    self.CHANNEL_NAMES[name] = cls.NEXT_CHANNEL
                    attr_name = 'CHANNEL_' + str(cls.NEXT_CHANNEL)
                    setattr(cls, attr_name, channel)
                    cls.NEXT_CHANNEL += 1
                self.client.print('Opening the', name, 'channel ...')
                return channel.connect(self.client)
        self.client.print('Channel name may not be empty.')

    # noinspection PyUnusedLocal
    def do_contacts(self, args):
        """Opens up your contacts list and allows you to edit it."""
        return internal.ContactManager(self.client)

    def do_eval(self, args):
        """Proof of concept: this is a math expression evaluator."""
        version = args[0] if args else self.client.input('Version?')
        if version == 'old':
            return math_engine_1.MathExpressionEvaluator(self.client)
        elif version == 'new':
            return math_engine_2.MathEvaluator(self.client)
        self.client.print('Try old or new.')

    # noinspection PyUnusedLocal
    def do_messages(self, args):
        """Opens up your account's inbox to read and send messages."""
        return internal.MessageManager(self.client)

    # noinspection PyUnusedLocal
    def do_options(self, args):
        """You can change some your settings with this command."""
        return internal.AccountOptions(self.client)
