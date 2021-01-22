import logging
import sqlite3
import threading
from typing import List

import constants

logger = logging.getLogger('database')
logger.setLevel(logging.DEBUG)

lock = threading.Lock()


class Database(object):
    def __init__(self):
        logger.debug(f"Connected to '{constants.DATABASE}'")
        self.conn = sqlite3.connect(constants.DATABASE)
        self.__isClosed = False

    @property
    def is_closed(self) -> bool:
        return self.__isClosed

    def close(self) -> None:
        """
        Closes the database connection and record it's connection status.
        """
        if self.__isClosed:
            logger.warning(f'Database connection is already closed.', exc_info=True)
        else:
            self.conn.close()
            self.__isClosed = True

    def construct(self):
        with lock:
            cur = self.conn.cursor()
            try:
                # check if the table exists
                cur.execute('''SELECT name FROM sqlite_master WHERE type='table' AND name='?';''', 'message')
                # if it doesn't exist, create the table and report it
                if cur.fetchone() is None:
                    self.conn.execute('''CREATE TABLE message
                                        (id INTEGER PRIMARY KEY,
                                        nickname TEXT NOT NULL,
                                        connection_hash TEXT NOT NULL,
                                        color TEXT DEFAULT '#000000',
                                        message TEXT DEFAULT '',
                                        timestamp INTEGER NOT NULL)''')
                    logger.debug("'message' table created.")
            finally:
                cur.close()

    def add_message(self, nickname: str, user_hash: str, color: str, message: str, timestamp: int) -> int:
        """
        Insert a message into the database. Returns the message ID.

        :param nickname: A non-unique identifier for the user.
        :param user_hash: A unique hash (usually) denoting the sender's identity.
        :param color: The color of the user who sent the message.
        :param message: The string content of the message echoed to all clients.
        :param timestamp: The epoch time of the sent message.
        :return: The unique integer primary key chosen for the message, i.e. it's ID.
        """
        with lock:
            with self.conn:
                cur = self.conn.cursor()
                try:
                    cur.execute('''INSERT INTO message (nickname, connection_hash, color, message, timestamp)
                                VALUES (?, ?, ?, ?, ?)''', [nickname, user_hash, color, message, timestamp])
                    logger.debug(f'Message {cur.lastrowid} recorded.')
                    return cur.lastrowid
                finally:
                    cur.close()

    def get_messages(self, columns: List[str] = None):
        with lock:
            cur = self.conn.cursor()
            try:
                if columns is None:
                    cur.execute('''SELECT * FROM message''')
                    return cur.fetchall()
            finally:
                cur.close()
