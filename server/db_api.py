#! /usr/bin/env python3
"""Creates a database application programmer interface for the program.

Before this module was created, all program data that needed to persist was
either stored in memory or stored as pickle files on disk. The purpose of the
code shown below is to switch data persistence to rely on sqlite3 instead."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '27 December 2017'
__version__ = 1, 0, 4
__all__ = [
    'DatabaseManager'
]

import contextlib
import hashlib
import operator
import pickle
import random
import sqlite3
import threading
import uuid


class DatabaseManager:
    """DatabaseManager(path) -> DatabaseManager instance"""

    def __init__(self, path):
        """Initialize the database and run the startup script if needed."""
        prime = not path.exists()
        self.__connection = sqlite3.connect(str(path), check_same_thread=False)
        with self.__cursor as cursor:
            cursor.execute('PRAGMA foreign_keys = ON')
        self.__connection.row_factory = sqlite3.Row
        self.__writing_lock = threading.Lock()
        if prime:
            self.__prime_database()

    def __enter__(self):
        """Allow instances to be used as context managers."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finish all database processing and pass all errors through."""
        self.__connection.commit()
        self.__connection.close()

    @property
    def __cursor(self):
        """Property that simplifies accessing database cursors."""
        return contextlib.closing(self.__connection.cursor())

    def __prime_database(self):
        """Execute the database creation script for table initialization."""
        with self.__cursor as cursor, \
                open('Confabulator_Database_create.sql', 'rt') as file, \
                self.__writing_lock:
            cursor.executescript(file.read())
        # Populate the database with values the script does not create.
        self.global_setting['InsideMenu.mercy_limit'] = 2
        self.global_setting['Application.name'] = 'Confabulator'
        self.__create_privilege_groups()
        self.__create_privilege_relationships()

    def __create_privilege_groups(self):
        """Create all the privilege groups needed for user accounts."""
        # Individual Table CRUD
        self.privilege_group_create('MutedUser.create')
        self.privilege_group_create('MutedUser.read')
        self.privilege_group_create('MutedUser.update')
        self.privilege_group_create('MutedUser.delete')
        self.privilege_group_create('ChannelBan.create')
        self.privilege_group_create('ChannelBan.read')
        self.privilege_group_create('ChannelBan.update')
        self.privilege_group_create('ChannelBan.delete')
        self.privilege_group_create('CommunicationChannel.create')
        self.privilege_group_create('CommunicationChannel.read')
        self.privilege_group_create('CommunicationChannel.update')
        self.privilege_group_create('CommunicationChannel.delete')
        self.privilege_group_create('InboxMessage.create')
        self.privilege_group_create('InboxMessage.read')
        self.privilege_group_create('InboxMessage.update')
        self.privilege_group_create('InboxMessage.delete')
        self.privilege_group_create('ChannelMessage.create')
        self.privilege_group_create('ChannelMessage.read')
        self.privilege_group_create('ChannelMessage.update')
        self.privilege_group_create('ChannelMessage.delete')
        self.privilege_group_create('UserContact.create')
        self.privilege_group_create('UserContact.read')
        self.privilege_group_create('UserContact.update')
        self.privilege_group_create('UserContact.delete')
        # Composite CRUD Privileges
        self.privilege_group_create('CREATE_ALL')
        self.privilege_group_create('READ_ALL')
        self.privilege_group_create('UPDATE_ALL')
        self.privilege_group_create('DELETE_ALL')
        self.privilege_group_create('FULL_CRUD')
        # Primary Account Privileges
        self.privilege_group_create('USER')
        self.privilege_group_create('ADMINISTRATOR')
        # Extra Administrator Permissions
        self.privilege_group_create('AdminConsole.open')
        self.privilege_group_create('ChannelAdmin.open')
        self.privilege_group_create('ChannelServer.open')
        self.privilege_group_create('ALL_ADMIN_POWER')

    def __create_privilege_relationships(self):
        """Build the hierarchy needed to support advanced permissions."""
        # All Creating Permissions
        self.privilege_relationship_create(
            'MutedUser.create', 'CREATE_ALL'
        )
        self.privilege_relationship_create(
            'ChannelBan.create', 'CREATE_ALL'
        )
        self.privilege_relationship_create(
            'CommunicationChannel.create', 'CREATE_ALL'
        )
        self.privilege_relationship_create(
            'InboxMessage.create', 'CREATE_ALL'
        )
        self.privilege_relationship_create(
            'ChannelMessage.create', 'CREATE_ALL'
        )
        self.privilege_relationship_create(
            'UserContact.create', 'CREATE_ALL'
        )
        # All Reading Permissions
        self.privilege_relationship_create(
            'MutedUser.read', 'READ_ALL'
        )
        self.privilege_relationship_create(
            'ChannelBan.read', 'READ_ALL'
        )
        self.privilege_relationship_create(
            'CommunicationChannel.read', 'READ_ALL'
        )
        self.privilege_relationship_create(
            'InboxMessage.read', 'READ_ALL'
        )
        self.privilege_relationship_create(
            'ChannelMessage.read', 'READ_ALL'
        )
        self.privilege_relationship_create(
            'UserContact.read', 'READ_ALL'
        )
        # All Updating Permissions
        self.privilege_relationship_create(
            'MutedUser.update', 'UPDATE_ALL'
        )
        self.privilege_relationship_create(
            'ChannelBan.update', 'UPDATE_ALL'
        )
        self.privilege_relationship_create(
            'CommunicationChannel.update', 'UPDATE_ALL'
        )
        self.privilege_relationship_create(
            'InboxMessage.update', 'UPDATE_ALL'
        )
        self.privilege_relationship_create(
            'ChannelMessage.update', 'UPDATE_ALL'
        )
        self.privilege_relationship_create(
            'UserContact.update', 'UPDATE_ALL'
        )
        # All Deleting Permissions
        self.privilege_relationship_create(
            'MutedUser.delete', 'DELETE_ALL'
        )
        self.privilege_relationship_create(
            'ChannelBan.delete', 'DELETE_ALL'
        )
        self.privilege_relationship_create(
            'CommunicationChannel.delete', 'DELETE_ALL'
        )
        self.privilege_relationship_create(
            'InboxMessage.delete', 'DELETE_ALL'
        )
        self.privilege_relationship_create(
            'ChannelMessage.delete', 'DELETE_ALL'
        )
        self.privilege_relationship_create(
            'UserContact.delete', 'DELETE_ALL'
        )
        # All CRUD Permissions
        self.privilege_relationship_create(
            'CREATE_ALL', 'FULL_CRUD'
        )
        self.privilege_relationship_create(
            'READ_ALL', 'FULL_CRUD'
        )
        self.privilege_relationship_create(
            'UPDATE_ALL', 'FULL_CRUD'
        )
        self.privilege_relationship_create(
            'DELETE_ALL', 'FULL_CRUD'
        )
        # All Account Permissions
        self.privilege_relationship_create(
            'FULL_CRUD', 'USER'
        )
        # Additional Administrator Privileges
        self.privilege_relationship_create(
            'FULL_CRUD', 'ADMINISTRATOR'
        )
        self.privilege_relationship_create(
            'AdminConsole.open', 'ALL_ADMIN_POWER'
        )
        self.privilege_relationship_create(
            'ChannelAdmin.open', 'ALL_ADMIN_POWER'
        )
        self.privilege_relationship_create(
            'ChannelServer.open', 'ALL_ADMIN_POWER'
        )
        self.privilege_relationship_create(
            'ALL_ADMIN_POWER', 'ADMINISTRATOR'
        )

    def ban_filter_is_banned(self, ip_address):
        """Check if the IP address is considered banned or not."""
        with self.__cursor as cursor:
            cursor.execute('''\
SELECT count(*) AS count
  FROM blocked_client
 WHERE ip_address = :ip_address''', dict(ip_address=ip_address))
            return cursor.fetchone()['count'] != 0

    def ban_filter_add(self, ip_address):
        """Add an IP address to the ban list if possible."""
        with self.__cursor as cursor, self.__writing_lock:
            cursor.execute('''\
INSERT INTO blocked_client (ip_address)
     VALUES (:ip_address)''', dict(ip_address=ip_address))

    def ban_filter_remove(self, ip_address):
        """Remove a banned IP address without checking for its existence."""
        with self.__cursor as cursor, self.__writing_lock:
            cursor.execute('''\
DELETE FROM blocked_client
      WHERE ip_address = :ip_address''', dict(ip_address=ip_address))

    def ban_filter_list(self):
        """Return all banned IP addresses in a tuple."""
        with self.__cursor as cursor:
            cursor.execute('''\
  SELECT ip_address
    FROM blocked_client
ORDER BY blocked_client_id''')
            return tuple(map(
                operator.itemgetter('ip_address'), cursor.fetchall()
            ))

    @property
    def global_setting(self):
        """Property that allows access to the global_setting table."""
        return GlobalSetting(self.__cursor, self.__writing_lock)

    def privilege_group_create(self, name):
        """Allows creation of a privilege group if it does not exist."""
        with self.__cursor as cursor, self.__writing_lock:
            cursor.execute('''\
INSERT INTO privilege_group (name)
     VALUES (:name)''', dict(name=name))

    def privilege_group_delete(self, name):
        """Allows the deletion of a privilege group not in a relationship."""
        with self.__cursor as cursor, self.__writing_lock:
            cursor.execute('''\
DELETE FROM privilege_group
      WHERE name = :name''', dict(name=name))

    def privilege_group_get_id(self, name):
        """Allows retrieval of the primary key for a privilege group."""
        with self.__cursor as cursor:
            cursor.execute('''\
SELECT privilege_group_id
  FROM privilege_group
 WHERE name = :name''', dict(name=name))
            return cursor.fetchone()['privilege_group_id']

    def privilege_relationship_create(self, parent, child):
        """Allows a privilege relationship to be created."""
        with self.__cursor as cursor, self.__writing_lock:
            cursor.execute('''\
INSERT INTO privilege_relationship (parent_id, child_id)
     VALUES (
    (SELECT privilege_group_id
       FROM privilege_group
      WHERE name = :parent),
    (SELECT privilege_group_id
       FROM privilege_group
      WHERE name = :child))''', dict(parent=parent, child=child))

    def privilege_relationship_delete(self, parent, child):
        """Allows a privilege relationship to be deleted."""
        with self.__cursor as cursor, self.__writing_lock:
            cursor.execute('''\
DELETE FROM privilege_relationship
      WHERE parent_id = (
     SELECT privilege_group_id
       FROM privilege_group
      WHERE name = :parent)
        AND child_id = (
     SELECT privilege_group_id
       FROM privilege_group
      WHERE name = :child)''', dict(parent=parent, child=child))

    def privilege_relationship_child_has_parent(self, child, parent):
        """Checks if a child is the descendant of a particular parent."""
        with self.__cursor as cursor:
            # Reference: https://stackoverflow.com/q/47947815/216356
            cursor.execute('''\
WITH RECURSIVE parent_of_child(id)
            AS (
        SELECT privilege_group_id
          FROM privilege_group
         WHERE name = :child
         UNION
        SELECT parent_id
          FROM privilege_relationship
          JOIN parent_of_child
            ON id = child_id)
        SELECT id
          FROM parent_of_child
         WHERE id = (
        SELECT privilege_group_id
          FROM privilege_group
         WHERE name = :parent)''', dict(child=child, parent=parent))
            return bool(cursor.fetchone())

    # TODO https://stackoverflow.com/q/47947581/216356

    def user_account_create(self, name, online, password, forgiven):
        """Creates new user with right privileges, and returns account ID."""
        password_salt = uuid.uuid4().bytes
        password_hash = self.__hash_password(password, password_salt)
        with self.__cursor as cursor:
            with self.__writing_lock:
                # With Writing Lock
                cursor.execute('''\
INSERT INTO user_account (
            name,
            online,
            password_salt,
            password_hash,
            forgiven,
            privilege_group_id)
     VALUES (
            :name,
            :online,
            :password_salt,
            :password_hash,
            :forgiven,
    (SELECT privilege_group_id
       FROM privilege_group
      WHERE name = CASE (
     SELECT count(*)
       FROM user_account)
       WHEN 0 THEN 'ADMINISTRATOR'
              ELSE 'USER' END))''', dict(
                    name=name,
                    online=online,
                    password_salt=password_salt,
                    password_hash=password_hash,
                    forgiven=forgiven
                ))
            # Without Writing Lock
            cursor.execute('''\
SELECT user_account_id
  FROM user_account
 WHERE name = :name''', dict(name=name))
            return cursor.fetchone()['user_account_id']

    def __hash_password(self, password, salt, encoding='latin_1'):
        """Creates a hash for a password in a slightly random process."""
        items_to_hash = [
            password.encode(encoding),
            salt,
            self.global_setting['Application.name'].encode(encoding)
        ]
        random.SystemRandom().shuffle(items_to_hash)
        return hashlib.sha512(b''.join(items_to_hash)).digest()

    def user_contact_get_contact_counts(self, owner_id):
        """Find out how many contacts are online for the given user."""
        with self.__cursor as cursor:
            cursor.execute('''\
SELECT (
SELECT count(*)
  FROM user_contact
 WHERE owner_id = :owner_id) AS all_contacts, (
SELECT count(*)
  FROM user_contact
  JOIN user_account
    ON user_contact.friend_id = user_account.user_account_id
 WHERE user_contact.owner_id = :owner_id
   AND user_account.online = :python_true) AS online_contacts''', dict(
                owner_id=owner_id, python_true=True
            ))
            return dict(cursor.fetchone())


class GlobalSetting:
    """GlobalSetting(cursor, writing_lock) -> GlobalSetting instance"""

    def __init__(self, cursor, writing_lock):
        """Initialize a one-time-use accessor and mutator for settings."""
        self.__cursor = cursor
        self.__writing_lock = writing_lock

    def __getitem__(self, key):
        """Get an arbitrary object out of the global setting system."""
        with self.__cursor as cursor:
            cursor.execute('''\
SELECT value
  FROM global_setting
 WHERE "key" = :key''', dict(key=key))
            return pickle.loads(cursor.fetchone()['value'])

    def __setitem__(self, key, value):
        """Assign an arbitrary object to a specific string key in settings."""
        with self.__cursor as cursor, self.__writing_lock:
            cursor.execute('''\
INSERT OR REPLACE INTO global_setting ("key", value)
                VALUES (:key, :value)''', dict(
                key=key, value=pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
            ))

    def __delitem__(self, key):
        """Delete the specified key/value pair from global settings."""
        with self.__cursor as cursor, self.__writing_lock:
            cursor.execute('''\
DELETE FROM global_setting
      WHERE "key" = :key''', dict(key='test'))
