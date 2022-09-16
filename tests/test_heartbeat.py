import socket
import time

import pytest

from shared import constants
from shared import protocol
from shared.exceptions import DataReceptionException
from server.handler import Client


def make_client():
    server_end, peer = socket.socketpair()
    return Client(server_end, ('127.0.0.1', 5555), [], lambda: False), peer


def test_heartbeat_pings_a_quiet_client():
    client, peer = make_client()
    client.last_seen = time.time() - constants.PING_INTERVAL - 1
    client.last_ping = 0
    client.heartbeat()
    assert protocol.read_message(peer)['type'] == constants.Types.PING
    assert client.last_ping > 0


def test_heartbeat_stays_quiet_for_a_recently_active_client():
    client, peer = make_client()
    client.last_seen = time.time()
    client.heartbeat()
    peer.settimeout(0.1)
    with pytest.raises(socket.timeout):
        protocol.read_message(peer)


def test_heartbeat_drops_a_stale_client():
    client, _ = make_client()
    client.last_seen = time.time() - constants.PING_TIMEOUT - 1
    with pytest.raises(DataReceptionException):
        client.heartbeat()
