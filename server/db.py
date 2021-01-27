import logging
import os
import sqlite3
import threading
import abc

import constants

logger = logging.getLogger('database')
logger.setLevel(logging.DEBUG)

lock = threading.Lock()


class Database(abc.ABC):
    def __init__(self, database: str):
        logger.debug(f"Connected to './{os.path.basename(database)}'")
        self.conn = sqlite3.connect(database, detect_types=sqlite3.PARSE_DECLTYPES)
        self.__isClosed = False
        self.__table = None
        self.construct()

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

    def construct(self) -> None:
        with lock:
            cur = self.conn.cursor()
            try:
                cur.execute('''SELECT name FROM sqlite_master WHERE type='table' AND name = ?;''', [self.__table])
                if cur.fetchone() is None:
                    self._construct()
                    logger.info(f"'{self.__table}' table created.")
            finally:
                cur.close()

    @abc.abstractmethod
    def _construct(self) -> None:
        pass


class ClientDatabase(Database):
    def __init__(self):
        super().__init__(constants.CLIENT_DATABASE)
        self.__table = 'connection'

    def _construct(self) -> None:
        self.conn.execute('''CREATE TABLE connection
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

    def _construct(self):
        self.conn.execute('''CREATE TABLE message
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
                    logger.debug(f'Message {cur.lastrowid} recorded.')
                    return cur.lastrowid
                finally:
                    cur.close()
