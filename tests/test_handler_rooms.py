import socket

import pytest

from shared import protocol
from server.handler import Client


def make_client(clients, nickname, room='general'):
    server_end, peer = socket.socketpair()
    client = Client(server_end, ('127.0.0.1', 5555), clients, lambda: False)
    client.nickname = nickname
    client.room = room
    clients.append(client)
    return client, peer


def test_send_connections_list_only_includes_roommates():
    clients = []
    alice, alice_peer = make_client(clients, 'alice', room='general')
    make_client(clients, 'bob', room='general')
    make_client(clients, 'carol', room='games')

    alice.send_connections_list()
    users = protocol.read_message(alice_peer)['users']
    names = {user['nickname'] for user in users}
    assert names == {'alice', 'bob'}


def test_notify_room_reaches_every_member_of_that_room():
    clients = []
    alice, alice_peer = make_client(clients, 'alice', room='general')
    bob, bob_peer = make_client(clients, 'bob', room='general')
    carol, carol_peer = make_client(clients, 'carol', room='games')
    carol_peer.settimeout(0.2)

    alice.notify_room('general')
    assert {u['nickname'] for u in protocol.read_message(alice_peer)['users']} == {'alice', 'bob'}
    assert {u['nickname'] for u in protocol.read_message(bob_peer)['users']} == {'alice', 'bob'}
    # carol is in another room and must not receive the general user list
    with pytest.raises(socket.timeout):
        protocol.read_message(carol_peer)
