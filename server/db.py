import logging
import sqlite3
from typing import List

import constants

logger = logging.getLogger('database')

conn = sqlite3.connect(constants.DATABASE)
logger.debug(f"Connected to '{constants.DATABASE}'")

logger.debug("Constructing 'message' table.")
conn.execute('''CREATE TABLE IF NOT EXISTS message
            (id INTEGER PRIMARY KEY,
            nickname TEXT NOT NULL,
            connection_hash TEXT NOT NULL,
            color TEXT DEFAULT '#000000',
            message TEXT DEFAULT '',
            timestamp INTEGER NOT NULL)''')
conn.commit()


def add_message(nickname: str, user_hash: str, color: str, message: str, timestamp: int) -> int:
    """
    Insert a message into the database. Returns the message ID.

    :param nickname: A non-unique identifier for the user.
    :param user_hash: A unique hash (usually) denoting the sender's identity.
    :param color: The color of the user who sent the message.
    :param message: The string content of the message echoed to all clients.
    :param timestamp: The epoch time of the sent message.
    :return: The unique integer primary key chosen for the message, i.e. it's ID.
    """
    cur = conn.cursor()
    try:
        cur.execute('''INSERT INTO message (nickname, connection_hash, color, message, timestamp)
                    VALUES (?, ?, ?, ?, ?)''', [nickname, user_hash, color, message, timestamp])
        conn.commit()
        logger.debug(f'Message {cur.lastrowid} recorded.')
        return cur.lastrowid
    finally:
        cur.close()


def get_messages(columns: List[str] = None):
    cur = conn.cursor()
    try:
        if columns is None:
            cur.execute('''SELECT * FROM message''')
            return cur.fetchall()
    finally:
        cur.close()
