import json
import logging
import random
import socket
import time
import uuid
from json import JSONDecodeError
from typing import Any, Callable, List, Optional

from shared import constants
from shared import helpers
from shared import protocol
# noinspection PyUnresolvedReferences
from shared.exceptions import DataReceptionException, StopException
from server import db
from server import rooms
from server import resilience
from server.commands import CommandHandler

logger = logging.getLogger('handler')
logger.setLevel(logging.DEBUG)


class BaseClient(object):
    """A simple base class for the client containing basic client communication methods."""

    def __init__(self, conn: socket.socket, all_clients: List['Client'], address, stop_flag: Callable[[], bool]) -> None:
        self.conn, self.all_clients, self.address, self.stop_flag = conn, all_clients, address, stop_flag
        self.db: Optional[db.ServerDatabase] = None

        self.conn.settimeout(0.5)

    def connect_database(self):
        """"""
        if self.db is None:
            logger.debug('Connecting client to database.')
            self.db = db.ServerDatabase()

    def send(self, message: bytes) -> None:
        """Sends a pre-encoded message to this client."""
        self.conn.send(message)

    def send_message(self, message: str) -> None:
        """Sends a string message as the server to this client."""
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
        for client in rooms.members_in(self.all_clients, getattr(self, 'room', constants.DEFAULT_ROOM)):
            client.send(prepared)

    def broadcast(self, message: bytes) -> None:
        """Sends a pre-encoded message to all clients in the sender's room"""
        for client in rooms.members_in(self.all_clients, getattr(self, 'room', constants.DEFAULT_ROOM)):
            client.send(message)

    def __repr__(self) -> str:
        return f'BaseClient({self.address})'


class Client(BaseClient):
    """
    A class dedicating to handling interactions between the server and the client.

    Client.run() should be ran in a thread alongside the other clients.
    """

    def __init__(self, conn: socket.socket, address: Any, all_clients: List['Client'], stop_flag: Callable[[], bool]):
        super().__init__(conn, all_clients, address, stop_flag)

        self.id = str(uuid.uuid4())
        self.short_id = self.id[:8]
        self.nickname = self.id[:8]
        self.room = constants.DEFAULT_ROOM
        self.color: constants.Color = random.choice(constants.Colors.has_contrast(float(constants.MINIMUM_CONTRAST)))

        self.command = CommandHandler(self)
        self.first_seen = time.time()
        self.last_nickname_change = None
        self.last_seen = time.time()
        self.last_ping = 0.0

    def __repr__(self) -> str:
        if self.last_nickname_change is None:
            return f'Client({self.short_id})'
        return f'Client({self.nickname}, {self.short_id})'

    def connect_database(self) -> None:
        """Instantiate"""
        if self.db is None:
            logger.debug(f'Connecting Client({self.short_id}) to the database.')
            self.db = db.ServerDatabase()

    def request_nickname(self) -> None:
        """Send a request for the client's nickname information."""
        self.conn.send(helpers.prepare_request(constants.Requests.REQUEST_NICK))

    def _room_user_list(self, room: str) -> bytes:
        """Encode the USER_LIST of everyone currently in `room`."""
        mates = rooms.members_in(self.all_clients, room)
        return helpers.prepare_json(
                {
                    'type': constants.Types.USER_LIST,
                    'users': [{'nickname': other.nickname, 'color': other.color.hex} for other in mates]
                }
        )

    def send_connections_list(self) -> None:
        """Sends this client the list of users sharing its room."""
        self.conn.send(self._room_user_list(self.room))

    def notify_room(self, room: str) -> None:
        """Send every member of `room` a refreshed user list."""
        payload = self._room_user_list(room)
        for member in rooms.members_in(self.all_clients, room):
            member.send(payload)

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
        """
        Attempt to receive raw data over the TCP Socket connection.

        This function takes use of the thread's Stop flag, and thus will raise a StopException automatically.
        This function will raise and intercept socket.timeout exceptions regularly until a message header is received.
        """

        while True:
            try:
                # Check if the stop flag has been set. Exceptions will be handled by parent function (handle).
                self.check_stop()

                # This will timeout in 0.5 seconds.
                header = protocol.recv_exact(self.conn, protocol.HEADER_LENGTH)
                break
            except socket.timeout:
                # No data this cycle; use the idle time to run the keep-alive.
                self.heartbeat()
                continue
            except ConnectionError:
                raise DataReceptionException('The connection closed before a header arrived.')

        try:
            length = int(header.decode('utf-8'))
        except ValueError:
            raise DataReceptionException('The socket did not receive the expected header.')

        logger.debug(f'Header received - Length {length}')

        try:
            data = json.loads(protocol.recv_exact(self.conn, length).decode('utf-8'))
        except ConnectionError:
            raise DataReceptionException('The connection closed mid-message.')
        except JSONDecodeError:
            raise DataReceptionException('The socket received a invalid JSON structure.')
        else:
            self.last_seen = time.time()
            logger.info(f'Data received/parsed, type: {data["type"]}')
            return data

    def handle_nickname(self, nickname: str) -> None:
        if self.last_nickname_change is None:
            logger.info(f'Nickname is {nickname}')
            self.broadcast_message(f'{nickname} joined!')
            self.last_nickname_change = time.time()
        else:
            logger.info(f'{self.nickname} changed their name to {nickname}')
        self.nickname = nickname

        # New nickname has to be sent to everyone sharing the room
        self.notify_room(self.room)

    def heartbeat(self) -> None:
        """Probe a quiet client with a PING, or drop one that has gone silent too long."""
        now = time.time()
        if resilience.is_stale(self.last_seen, now, constants.PING_TIMEOUT):
            raise DataReceptionException('The client stopped responding.')
        if resilience.should_ping(self.last_seen, self.last_ping, now, constants.PING_INTERVAL):
            self.conn.send(helpers.prepare_ping())
            self.last_ping = now

    def check_stop(self) -> None:
        """Raises a StopException if the stop flag is set to true by the commanding main thread."""
        stop_flag: bool = self.stop_flag()
        if stop_flag:
            raise StopException()

    def close(self) -> None:
        logger.info(f'Shutting down Client {self.id}. ({self.nickname})')
        self.conn.close()  # Close socket connection
        self.all_clients.remove(self)  # Remove the user from the global client list
        self.broadcast_message(f'{self.nickname} left!')  # Now we can broadcast it's exit message
        # Inform the room's remaining members of the disconnect
        self.notify_room(self.room)
        self.db.close()  # Close database connection

    def handle(self) -> None:
        """Server mainloop function for a given socket connection"""

        self.connect_database()  # Initialize a database connection

        while True:
            try:
                logger.info('Waiting to received data')
                data = self.receive()

                if data['type'] == constants.Types.REQUEST:
                    if data['request'] == constants.Requests.GET_MESSAGE_HISTORY:
                        self.send_message_history(
                                limit=data.get('limit', 50), time_limit=data.get('time_limit', 60 * 30)
                        )

                elif data['type'] == constants.Types.PONG:
                    pass  # last_seen was already refreshed in receive()
                elif data['type'] == constants.Types.QUIT:
                    logger.info(f'{self.nickname} sent QUIT, closing connection.')
                    self.close()
                    break
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
                logger.critical('Lost connection to the client.')
                self.close()
                break
            except StopException:
                logger.info('Stop flag received from main thread.')
                self.close()
                break
            except Exception as e:
                logger.critical(e, exc_info=True)
                self.close()
                break
