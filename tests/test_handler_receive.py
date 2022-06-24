import socket

import pytest

from shared import protocol
from shared.exceptions import DataReceptionException
from server.handler import Client


def make_client():
    server_end, client_end = socket.socketpair()
    client = Client(server_end, ('127.0.0.1', 5555), [], lambda: False)
    return client, client_end


def test_receive_reads_a_framed_message():
    client, peer = make_client()
    peer.sendall(protocol.encode({'type': 'MESSAGE', 'content': 'hi'}))
    data = client.receive()
    assert data['type'] == 'MESSAGE'
    assert data['content'] == 'hi'


def test_receive_reassembles_a_message_sent_in_pieces():
    client, peer = make_client()
    frame = protocol.encode({'type': 'MESSAGE', 'content': 'x' * 4000})
    peer.sendall(frame[:5])
    peer.sendall(frame[5:])
    assert client.receive()['content'] == 'x' * 4000


def test_receive_raises_on_a_closed_connection():
    client, peer = make_client()
    peer.close()
    with pytest.raises(DataReceptionException):
        client.receive()
