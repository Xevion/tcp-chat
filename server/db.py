import abc
import datetime
import logging
import os
import sqlite3
import threading
from typing import List, Optional

from shared import constants

logger = logging.getLogger('database')

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
            logger.warning('Database connection is already closed.', exc_info=True)
        else:
            self.conn.close()
            self.__isClosed = True

    @abc.abstractmethod
    def construct(self) -> None:
        self._construct()


class ClientDatabase(Database):
    def __init__(self, database: str = constants.CLIENT_DATABASE):
        super().__init__(database)

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

    def remember_connection(self, address: str, port: int, nickname: str, password: str = None) -> None:
        """Record a successful connection, bumping its use count if already known."""
        now = datetime.datetime.now()
        with lock:
            with self.conn:
                cur = self.conn.cursor()
                try:
                    cur.execute('SELECT id FROM connection WHERE address = ? AND port = ? AND nickname = ?',
                                [address, port, nickname])
                    row = cur.fetchone()
                    if row is None:
                        cur.execute('''INSERT INTO connection (address, port, nickname, password, initial_time, latest_time)
                                    VALUES (?, ?, ?, ?, ?, ?)''', [address, port, nickname, password, now, now])
                    else:
                        cur.execute('UPDATE connection SET connections = connections + 1, latest_time = ?, password = ? '
                                    'WHERE id = ?', [now, password, row[0]])
                finally:
                    cur.close()

    def last_connection(self) -> Optional[dict]:
        """Return the most recently used connection, or None if none are stored."""
        with lock:
            cur = self.conn.cursor()
            try:
                cur.execute('''SELECT address, port, nickname, password, favorite FROM connection
                            ORDER BY latest_time DESC LIMIT 1''')
                row = cur.fetchone()
            finally:
                cur.close()
        return self._as_connection(row)

    def recent_connections(self, limit: int = 10) -> List[dict]:
        """Return stored connections, most recently used first."""
        with lock:
            cur = self.conn.cursor()
            try:
                cur.execute('''SELECT address, port, nickname, password, favorite FROM connection
                            ORDER BY latest_time DESC LIMIT ?''', [limit])
                rows = cur.fetchall()
            finally:
                cur.close()
        return [self._as_connection(row) for row in rows]

    def favorite_connections(self) -> List[dict]:
        """Return the connections the user has starred, most recently used first."""
        with lock:
            cur = self.conn.cursor()
            try:
                cur.execute('''SELECT address, port, nickname, password, favorite FROM connection
                            WHERE favorite = 1 ORDER BY latest_time DESC''')
                rows = cur.fetchall()
            finally:
                cur.close()
        return [self._as_connection(row) for row in rows]

    def set_favorite(self, address: str, port: int, nickname: str, favorite: bool = True) -> None:
        """Flag or unflag a stored connection as a favorite."""
        with lock:
            with self.conn:
                self.conn.execute('UPDATE connection SET favorite = ? '
                                  'WHERE address = ? AND port = ? AND nickname = ?',
                                  [1 if favorite else 0, address, port, nickname])

    @staticmethod
    def _as_connection(row) -> Optional[dict]:
        """Turn a (address, port, nickname, password, favorite) row into a dict."""
        if row is None:
            return None
        return {'address': row[0], 'port': row[1], 'nickname': row[2],
                'password': row[3], 'favorite': bool(row[4])}


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
