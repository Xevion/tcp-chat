import json
import logging
import random
import socket
import time
import uuid
from typing import Any, List

import constants
import helpers
from server.commands import CommandHandler

logger = logging.getLogger('handler')


class BaseClient(object):
    """A simple base class for the client containing basic client communication methods."""

    def __init__(self, conn: socket.socket, all_clients: List['Client'], address) -> None:
        self.conn, self.all_clients, self.address = conn, all_clients, address

    def send(self, message: bytes) -> None:
        """Sends a pre-encoded message to this client."""
        self.conn.send(message)

    def send_message(self, message: str) -> None:
        """Sends a string message as the server to this client."""
        # db.add_message('Server', 'server', constants.Colors.BLACK.hex, message, int(time.time()))
        self.conn.send(helpers.prepare_message(
            nickname='Server', message=message, color=constants.Colors.BLACK.hex
        ))

    def broadcast_message(self, message: str) -> None:
        """Sends a string message to all connected clients as the Server."""
        db.add_message('Server', 'server', constants.Colors.BLACK.hex, message, int(time.time()))
        prepared = helpers.prepare_message(
            nickname='Server', message=message, color=constants.Colors.BLACK.hex
        )
        for client in self.all_clients:
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

    def receive(self) -> Any:
        length = int(self.conn.recv(constants.HEADER_LENGTH).decode('utf-8'))
        logger.debug(f'Header received - Length {length}')
        data = json.loads(self.conn.recv(length).decode('utf-8'))
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

    def handle(self) -> None:
        while True:
            try:
                data = self.receive()

                if data['type'] == constants.Types.REQUEST:
                    if data['request'] == constants.Requests.REFRESH_CONNECTIONS_LIST:
                        self.send_connections_list()
                elif data['type'] == constants.Types.NICKNAME:
                    self.handle_nickname(data['nickname'])
                elif data['type'] == constants.Types.MESSAGE:
                    self.broadcast(helpers.prepare_message(
                        nickname=self.nickname,
                        message=data['content'],
                        color=self.color.hex
                    ))

                    command = data['content'].strip()
                    if command.startswith('/'):
                        args = data['content'][1:].strip().split()
                        args[0] = args[0].lower()  # Command name will always be perceived as lowercase
                        msg = self.command.process(args)
                        if msg is not None:
                            self.broadcast_message(msg)

            except Exception as e:
                logger.critical(e, exc_info=True)
                logger.info(f'Client {self.id} closed. ({self.nickname})')
                self.conn.close()
                self.all_clients.remove(self)
                self.broadcast_message(f'{self.nickname} left!')
                break
