import sqlite3
from typing import List
import logging

import constants

logger = logging.getLogger('database')

conn = sqlite3.connect(constants.DATABASE)
logger.debug(f"Connected to '{constants.DATABASE}'")

logger.debug("Constructing 'message' table.")
cur = conn.cursor()
conn.execute('''CREATE TABLE IF NOT EXISTS message
            (id INTEGER PRIMARY KEY,
            nickname TEXT NOT NULL,
            connection_hash TEXT NOT NULL,
            color TEXT DEFAULT '#000000',
            message TEXT DEFAULT '',
            timestamp INTEGER NOT NULL)''')
conn.commit()


def add_message(nickname: str, hash: str, color: str, message: str, timestamp: int):
    cur.execute('''INSERT INTO message (nickname, connection_hash, color, message, timestamp)
                VALUES (?, ?, ?, ?, ?)''', [nickname, hash, color, message, timestamp])
    conn.commit()


def get_messages(columns: List[str] = None):
    if columns is None:
        cur.execute('''SELECT * FROM message''')
        return cur.fetchall()

