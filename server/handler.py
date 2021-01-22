import json
import logging
import random
import socket
import time
import uuid
from json import JSONDecodeError
from typing import Any, List, Optional

import constants
import helpers
# noinspection PyUnresolvedReferences
from exceptions import DataReceptionException
from server import db
from server.commands import CommandHandler
from server.db import Database

logger = logging.getLogger('handler')


class BaseClient(object):
    """A simple base class for the client containing basic client communication methods."""

    def __init__(self, conn: socket.socket, all_clients: List['Client'], address) -> None:
        self.conn, self.all_clients, self.address = conn, all_clients, address
        self.db: Optional[Database] = None

    def connect_database(self):
        if self.db is None:
            logger.debug('Connecting client to database.')
            self.db = Database()

    def send(self, message: bytes) -> None:
        """Sends a pre-encoded message to this client."""
        self.conn.send(message)

    def send_message(self, message: str) -> None:
        """Sends a string message as the server to this client."""
        # db.add_message('Server', 'server', constants.Colors.BLACK.hex, message, int(time.time()))
        self.conn.send(helpers.prepare_message(
            nickname='Server', message=message, color=constants.Colors.BLACK.hex, message_id=-1
        ))

    def broadcast_message(self, message: str) -> None:
        """Sends a string message to all connected clients as the Server."""
        timestamp = int(time.time())
        message_id = self.db.add_message('Server', 'server', constants.Colors.BLACK.hex, message, timestamp)
        prepared = helpers.prepare_message(
            nickname='Server', message=message, color=constants.Colors.BLACK.hex, message_id=message_id,
            timestamp=timestamp
        )
        for client in self.all_clients:
            print(f'Sending a message to {client.nickname}')
            client.send(prepared)

    def broadcast(self, message: bytes) -> None:
        """Sends a pre-encoded message to all connected clients"""
        for client in self.all_clients:
            client.send(message)

    def __repr__(self) -> str:
        return f'BaseClient({self.address})'


class Client(BaseClient):
    """
    A class dedicating to handling interactions between the server and the client.

    Client.run() should be ran in a thread alongside the other clients.
    """

    def __init__(self, conn: socket.socket, address: Any, all_clients: List['Client']):
        super().__init__(conn, all_clients, address)

        self.id = str(uuid.uuid4())
        self.nickname = self.id[:8]
        self.color: constants.Color = random.choice(constants.Colors.has_contrast(float(constants.MINIMUM_CONTRAST)))

        self.command = CommandHandler(self)
        self.first_seen = time.time()
        self.last_nickname_change = None
        self.last_message_sent = None

    def __repr__(self) -> str:
        if self.last_nickname_change is None:
            return f'Client({self.id[:8]})'
        return f'Client({self.nickname}, {self.id[:8]})'

    def connect_database(self) -> None:
        if self.db is None:
            logger.debug(f'Connecting Client({self.id[:8]}) to the database.')
            self.db = Database()

    def request_nickname(self) -> None:
        """Send a request for the client's nickname information."""
        self.conn.send(helpers.prepare_request(constants.Requests.REQUEST_NICK))

    def send_connections_list(self) -> None:
        """Sends a list of connections to the server, identifying their nickname and color"""
        self.conn.send(helpers.prepare_json(
            {
                'type': constants.Types.USER_LIST,
                'users': [{'nickname': other.nickname, 'color': other.color.hex} for other in self.all_clients]
            }
        ))

    def send_message_history(self, limit: int, time_limit: int) -> None:
        limit = min(100, max(0, limit))
        time_limit = min(60 * 30, max(0, time_limit))
        min_time = int(time.time()) - time_limit

        with db.lock:
            cur = self.db.conn.cursor()
            try:
                cur.execute('''SELECT id, nickname, color, message, timestamp
                                FROM message
                                WHERE timestamp >= ?
                                ORDER BY timestamp
                                LIMIT ?''',
                            [min_time, limit])

                messages = cur.fetchall()
                self.send(helpers.prepare_message_history(messages))
            finally:
                cur.close()

    def receive(self) -> Any:
        try:
            length = int(self.conn.recv(constants.HEADER_LENGTH).decode('utf-8'))
        except ValueError:
            raise DataReceptionException('The socket did not receive the expected header.')
        else:
            logger.debug(f'Header received - Length {length}')

        try:
            data = self.conn.recv(length).decode('utf-8')
            data = json.loads(data)
        except JSONDecodeError:
            raise DataReceptionException('The socket received a invalid JSON structure.')
        else:
            logger.info(f'Data received/parsed, type: {data["type"]}')
            return data

    def handle_nickname(self, nickname: str) -> None:
        if self.last_nickname_change is None:
            logger.info("Nickname is {}".format(nickname))
            self.broadcast_message(f'{nickname} joined!')
            self.last_nickname_change = time.time()
        else:
            logger.info(f'{self.nickname} changed their name to {nickname}')
        self.nickname = nickname

    def close(self) -> None:
        logger.info(f'Client {self.id} closed. ({self.nickname})')
        self.conn.close()  # Close socket connection
        self.all_clients.remove(self)  # Remove the user from the global client list
        self.broadcast_message(f'{self.nickname} left!')  # Now we can broadcast it's exit message
        self.db.conn.close()  # Close database connection

    def handle(self) -> None:
        self.connect_database()
        while True:
            try:
                data = self.receive()

                if data['type'] == constants.Types.REQUEST:
                    if data['request'] == constants.Requests.REFRESH_CONNECTIONS_LIST:
                        self.send_connections_list()
                    if data['request'] == constants.Requests.GET_MESSAGE_HISTORY:
                        self.send_message_history(
                            limit=data.get('limit', 50), time_limit=data.get('time_limit', 60 * 30)
                        )

                elif data['type'] == constants.Types.NICKNAME:
                    self.handle_nickname(data['nickname'])
                elif data['type'] == constants.Types.MESSAGE:
                    # Record the message in the DB.
                    message_id = self.db.add_message(self.nickname, self.id, self.color.hex, data['content'],
                                                     int(time.time()))

                    self.broadcast(helpers.prepare_message(
                        nickname=self.nickname,
                        message=data['content'],
                        color=self.color.hex,
                        message_id=message_id
                    ))

                    # Process commands
                    command = data['content'].strip()
                    if command.startswith('/'):
                        args = data['content'][1:].strip().split()
                        args[0] = args[0].lower()  # Command name will always be perceived as lowercase
                        msg = self.command.process(args)
                        if msg is not None:
                            self.broadcast_message(msg)
            except DataReceptionException as e:
                logger.critical(e)
                logger.warning('Aborting connection to the client.')
                self.close()
                break
            except ConnectionResetError:
                logger.critical('Lost connection to the client. Exiting.')
                self.close()
                break
            except Exception as e:
                logger.critical(e, exc_info=True)
                self.close()
                break
