import socket

from shared import constants
from shared import helpers
from shared import protocol


def decode(frame: bytes) -> dict:
    a, b = socket.socketpair()
    a.sendall(frame)
    return protocol.read_message(b)


def test_ping_pong_quit_frames():
    assert decode(helpers.prepare_ping())['type'] == constants.Types.PING
    assert decode(helpers.prepare_pong())['type'] == constants.Types.PONG
    assert decode(helpers.prepare_quit())['type'] == constants.Types.QUIT
