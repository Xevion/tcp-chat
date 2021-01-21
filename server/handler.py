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


class Client:
    """
    A class dedicating to handling interactions between the server and the client.

    Client.run() should be ran in a thread alongside the other clients.
    """

    def __init__(self, conn: socket.socket, address: Any, all_clients: List['Client']):
        self.conn, self.address = conn, address
        self.all_clients = all_clients

        self.id = str(uuid.uuid4())
        self.nickname = self.id[:8]
        self.color = random.choice(constants.Colors.ALL)

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

    def receive_message(self) -> Any:
        length = int(self.conn.recv(constants.HEADER_LENGTH).decode('utf-8'))
        logger.debug(f'Header received - Length {length}')
        message = json.loads(self.conn.recv(length).decode('utf-8'))
        logger.info(f'Data received/parsed, type: {message["type"]}')
        return message

    def handle_nickname(self, nickname: str) -> None:
        if self.last_nickname_change is None:
            logger.info("Nickname is {}".format(nickname))
            self.broadcast_message(f'{nickname} joined!')
            self.last_nickname_change = time.time()
        else:
            logger.info(f'{self.nickname} changed their name to {nickname}')
        self.nickname = nickname

    def send(self, message: bytes) -> None:
        """Sends a pre-encoded message to this client."""
        self.conn.send(message)

    def send_message(self, message: str) -> None:
        """Sends a string message as the server to this client."""
        self.conn.send(helpers.prepare_message(
            nickname='Server', message=message, color=constants.Colors.BLACK.hex
        ))

    def broadcast_message(self, message: str) -> None:
        """Sends a string message to all connected clients as the Server."""
        prepared = helpers.prepare_message(
            nickname='Server', message=message, color=constants.Colors.BLACK.hex
        )
        for client in self.all_clients:
            client.send(prepared)

    def broadcast(self, message: bytes) -> None:
        """Sends a pre-encoded message to all connected clients"""
        for client in self.all_clients:
            client.send(message)

    def handle(self) -> None:
        while True:
            try:
                data = self.receive_message()

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
                        msg = self.command.process(data['content'][1:].strip().split())
                        if msg is not None:
                            self.broadcast_message(msg)

            except Exception as e:
                logger.critical(e, exc_info=True)
                logger.info(f'Client {self.id} closed. ({self.nickname})')
                self.conn.close()
                self.broadcast_message(f'{self.nickname} left!')
                break
