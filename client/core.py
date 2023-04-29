"""Qt-free client core: everything about *talking to the server*, with no UI.

The GUI is a thin view over this module. The core owns connecting (including the
cleartext handshake and TLS upgrade), classifying a failure as permanent or
transient, the reconnect backoff, and the receive loop -- which it exposes as a
blocking generator of typed :class:`Event` values. Protocol bookkeeping (replying
to a nickname request, answering a PING) is handled here and never surfaces to the
view; only the domain events the UI renders come out of :meth:`ClientCore.events`.

Because there is no Qt here, the same object the GUI runs can be driven headless
in tests against a real server, so the tests and the UI exercise one code path.
"""

import json
import logging
import socket
from typing import Iterator, NamedTuple, Optional

from shared import constants
from shared import handshake
from shared import helpers
from shared import protocol
from shared.backoff import backoff_delays

logger = logging.getLogger('core')

# Domain event types yielded by ClientCore.events().
MESSAGE = 'message'        # payload: {nickname, message, color, time, id}
USER_LIST = 'user_list'    # payload: {users: [...]}
STATS = 'stats'            # payload: {sent: int, received: int} -- running byte totals
DISCONNECTED = 'disconnected'  # payload: {error: Exception|None}; terminates the stream


class Event(NamedTuple):
    type: str
    payload: dict


class ConnectResult(NamedTuple):
    ok: bool
    sock: Optional[socket.socket]
    reason: str = ''
    permanent: bool = False  # True when the server stated a refusal, so retrying is pointless


def open_connection(host: str, port: int, use_tls: bool = False, verify: bool = False,
                    version: int = protocol.PROTOCOL_VERSION, server_hostname: str = None,
                    timeout: float = None, is_probe: bool = False) -> ConnectResult:
    """Open a socket and run the client handshake, the one true 'connect' path.

    A real connection and a reachability probe both go through here, so the probe
    can never drift from what connecting actually does. ``timeout`` (when given)
    bounds both the TCP connect and the handshake; a real connect leaves it unset
    and then streams on a blocking socket. ``is_probe`` tells the server this is a
    reachability check it can answer and close, rather than a client to set up.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if timeout is not None:
        sock.settimeout(timeout)
    try:
        sock.connect((host, port))
    except OSError as e:
        sock.close()
        return ConnectResult(False, None, str(e))

    handshake_timeout = timeout if timeout is not None else handshake.HANDSHAKE_TIMEOUT
    result = handshake.negotiate_client(
        sock, want_tls=use_tls, version=version, verify=verify,
        server_hostname=server_hostname or host, timeout=handshake_timeout, is_probe=is_probe)
    if not result.ok:
        try:
            sock.close()
        except OSError:
            pass
        return ConnectResult(False, None, result.reason, permanent=result.rejected)

    result.sock.settimeout(None)  # the streaming phase blocks on recv
    return ConnectResult(True, result.sock)


class ProbeResult(NamedTuple):
    ok: bool
    detail: str


def probe(host: str, port: int, use_tls: bool = False, verify: bool = False,
          timeout: float = 3.0) -> ProbeResult:
    """Check whether a real connection would succeed, then drop it. Never raises.

    This is a connect dry-run: it runs the same handshake a client would, so a
    version or TLS mismatch is reported here exactly as it would be on connect.
    """
    result = open_connection(host, port, use_tls=use_tls, verify=verify,
                             timeout=timeout, is_probe=True)
    if result.sock is not None:
        try:
            result.sock.close()
        except OSError:
            pass
    if result.ok:
        return ProbeResult(True, 'Connection succeeded.')
    return ProbeResult(False, result.reason)


class ClientCore:
    """Owns the connection to one server for the lifetime of a chat session."""

    def __init__(self, host: str, port: int, nickname: str, use_tls: bool = False,
                 verify: bool = constants.TLS_VERIFY, version: int = protocol.PROTOCOL_VERSION):
        self.host, self.port, self.nickname = host, port, nickname
        self.use_tls, self.verify, self.version = use_tls, verify, version
        self.sock = None
        self.reason = ''
        self.permanent = False
        self.sent = 0
        self.received = 0
        self._delays = None

    def connect(self) -> ConnectResult:
        """(Re)open the connection, recording why it failed for the caller to act on."""
        result = open_connection(self.host, self.port, use_tls=self.use_tls,
                                 verify=self.verify, version=self.version,
                                 server_hostname=self.host)
        if result.ok:
            self.sock = result.sock
            self.reason, self.permanent = '', False
        else:
            self.reason, self.permanent = result.reason, result.permanent
        return result

    def events(self) -> Iterator[Event]:
        """Yield domain events until the connection drops, then a final DISCONNECTED.

        Frame reading, the byte-count stats, and protocol control replies all
        happen in here; the view just consumes the events it cares about.
        """
        try:
            while True:
                try:
                    raw_header = protocol.recv_exact(self.sock, protocol.HEADER_LENGTH)
                    length = int(raw_header.decode('utf-8'))
                    raw_body = protocol.recv_exact(self.sock, length)
                    message = json.loads(raw_body.decode('utf-8'))
                except Exception as e:
                    logger.log(logging.INFO, 'Connection closed: %s', e)
                    yield Event(DISCONNECTED, {'error': e})
                    return

                self.received += len(raw_header) + len(raw_body)
                yield Event(STATS, {'sent': self.sent, 'received': self.received})
                yield from self._dispatch(message)
        finally:
            self.close()

    def _dispatch(self, message: dict) -> Iterator[Event]:
        """Turn one decoded frame into events, answering protocol control inline."""
        kind = message['type']
        if kind == constants.Types.REQUEST:
            if message['request'] == constants.Requests.REQUEST_NICK:
                self._send(helpers.prepare_json(
                    {'type': constants.Types.NICKNAME, 'nickname': self.nickname}))
        elif kind == constants.Types.PING:
            self._send(helpers.prepare_pong())
        elif kind == constants.Types.MESSAGE:
            yield Event(MESSAGE, _extract_message(message))
        elif kind == constants.Types.USER_LIST:
            yield Event(USER_LIST, {'users': message['users']})
        elif kind == constants.Types.MESSAGE_HISTORY:
            for submessage in message['messages']:
                yield Event(MESSAGE, _extract_message(submessage))

    def _send(self, data: bytes) -> None:
        self.sent += len(data)
        self.sock.send(data)

    def send_message(self, text: str) -> None:
        """Send a chat message (or slash command) to the server."""
        text = text.strip()
        if text:
            self._send(helpers.prepare_json(
                {'type': constants.Types.MESSAGE, 'content': text}))

    def send_quit(self) -> None:
        """Tell the server we are leaving; safe to call on a dead socket."""
        try:
            self._send(helpers.prepare_quit())
        except OSError:
            pass  # socket already gone; nothing to announce

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass

    def next_reconnect_delay(self) -> float:
        """Next backoff delay, advancing the sequence; resets via reset_backoff()."""
        if self._delays is None:
            self._delays = backoff_delays()
        return next(self._delays)

    def reset_backoff(self) -> None:
        """Forget the current backoff so the next drop starts a fresh sequence."""
        self._delays = None


def _extract_message(data: dict) -> dict:
    return {
        'nickname': data['nickname'],
        'message': data['content'],
        'color': data['color'],
        'time': data['time'],
        'id': data['id'],
    }
