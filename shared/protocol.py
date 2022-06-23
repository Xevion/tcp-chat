"""Wire protocol framing shared by the server and client.

Messages travel as a fixed-width ASCII length header followed by a UTF-8 JSON
body. ``socket.recv(n)`` may return fewer than ``n`` bytes, so every read has to
loop until the whole frame has arrived -- otherwise large message bodies get
truncated and the JSON fails to parse.
"""

import json
from typing import Any

HEADER_LENGTH = 10

# Bumped whenever the message envelope changes in a way that isn't backwards
# compatible. Stamped onto every outgoing dict frame so both ends can tell which
# revision they are talking to.
PROTOCOL_VERSION = 1


def encode(obj: Any) -> bytes:
    """Encode an object as a length-prefixed UTF-8 JSON frame.

    Dict frames are stamped with the protocol version under the ``v`` key unless
    they already carry one. The input object is left untouched.
    """
    if isinstance(obj, dict) and 'v' not in obj:
        obj = dict(obj, v=PROTOCOL_VERSION)
    body = json.dumps(obj).encode('utf-8')
    header = '{:<{width}}'.format(len(body), width=HEADER_LENGTH).encode('utf-8')
    return header + body


def recv_exact(sock, length: int) -> bytes:
    """Receive exactly ``length`` bytes, looping until they have all arrived.

    Raises ConnectionError if the peer closes the connection before the frame is
    complete. A socket.timeout (when one is configured) propagates to the caller.
    """
    chunks = []
    remaining = length
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError('connection closed before frame was complete')
        chunks.append(chunk)
        remaining -= len(chunk)
    return b''.join(chunks)


def read_message(sock) -> dict:
    """Read and decode a single length-prefixed JSON frame from the socket."""
    header = recv_exact(sock, HEADER_LENGTH).decode('utf-8')
    length = int(header)
    body = recv_exact(sock, length).decode('utf-8')
    return json.loads(body)
