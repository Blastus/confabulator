#! /usr/bin/env python3
"""Creates a database application programmer interface for the program.

Before this module was created, all program data that needed to persist was
either stored in memory or stored as pickle files on disk. The purpose of the
code shown below is to switch data persistence to rely on sqlite3 instead."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '21 December 2017'
__version__ = 1, 0, 0
__all__ = [
    'DatabaseManager'
]

import contextlib
import operator
import sqlite3
import threading


class DatabaseManager:
    """DatabaseManager(path) -> DatabaseManager instance"""

    def __init__(self, path):
        """Initialize the database and run the startup script if needed."""
        prime = not path.exists()
        self.__connection = sqlite3.connect(str(path), check_same_thread=False)
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