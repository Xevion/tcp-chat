import abc
import logging
import os
import sqlite3
import threading
from typing import List, Optional, Union

from shared import constants

logger = logging.getLogger('database')
logger.setLevel(logging.DEBUG)

lock = threading.Lock()


class Database(abc.ABC):
    def __init__(self, database: str):
        self.conn = sqlite3.connect(database, detect_types=sqlite3.PARSE_DECLTYPES)
        logger.debug(f"Connected to './{os.path.basename(database)}'")
        self.__isClosed = False
        self._tables: List[str] = []
        self.construct()
        logger.debug('Completed database construction.')

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

    @abc.abstractmethod
    def construct(self) -> None:
        self._construct()


class ClientDatabase(Database):
    def __init__(self):
        super().__init__(constants.CLIENT_DATABASE)

    def construct(self) -> None:
        self.conn.execute('''CREATE TABLE IF NOT EXISTS connection
                            (id INTEGER PRIMARY KEY,
                            address TEXT NOT NULL,
                            port INTEGER NOT NULL,
                            nickname TEXT NOT NULL,
                            password TEXT,
                            connections INTEGER DEFAULT 1,
                            favorite BOOLEAN DEFAULT FALSE,
                            initial_time TIMESTAMP NOT NULL,
                            latest_time TIMESTAMP NOT NULL);''')


class ServerDatabase(Database):
    def __init__(self):
        super().__init__(constants.SERVER_DATABASE)

    def construct(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS message
                            (id INTEGER PRIMARY KEY,
                            nickname TEXT NOT NULL,
                            connection_hash TEXT NOT NULL,
                            color TEXT DEFAULT '#000000',
                            message TEXT DEFAULT '',
                            timestamp INTEGER NOT NULL)''')

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
                    logger.debug(f'Message #{cur.lastrowid} recorded.')
                    return cur.lastrowid
                finally:
                    cur.close()
