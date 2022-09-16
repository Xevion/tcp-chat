import socket

from shared import helpers
from server import resilience
from server.handler import Client


def test_is_stale():
    assert resilience.is_stale(last_seen=0, now=61, timeout=60) is True
    assert resilience.is_stale(last_seen=0, now=60, timeout=60) is False


def test_should_ping():
    # quiet long enough and not recently probed -> ping
    assert resilience.should_ping(last_seen=0, last_ping=0, now=20, interval=20) is True
    # already probed within the interval -> wait
    assert resilience.should_ping(last_seen=0, last_ping=15, now=20, interval=20) is False
    # still chatty -> no need
    assert resilience.should_ping(last_seen=18, last_ping=0, now=20, interval=20) is False


def test_receive_refreshes_last_seen():
    server_end, peer = socket.socketpair()
    client = Client(server_end, ('127.0.0.1', 5555), [], lambda: False)
    client.last_seen = 0
    peer.sendall(helpers.prepare_pong())
    data = client.receive()
    assert data['type'] == 'PONG'
    assert client.last_seen > 0
