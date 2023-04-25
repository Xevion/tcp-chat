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


def test_bare_slash_is_not_treated_as_a_command():
    clients = []
    alice, alice_peer = make_client(clients, 'alice')
    alice_peer.settimeout(0.2)

    # A lone '/' has no command name; it must not raise (it used to IndexError on
    # args[0]) and must not produce a command reply.
    alice.process_command('/')

    with pytest.raises(socket.timeout):
        protocol.read_message(alice_peer)


def test_slash_with_only_whitespace_is_not_treated_as_a_command():
    clients = []
    alice, alice_peer = make_client(clients, 'alice')
    alice_peer.settimeout(0.2)

    alice.process_command('/   ')

    with pytest.raises(socket.timeout):
        protocol.read_message(alice_peer)


def test_slash_command_still_runs_and_replies():
    clients = []
    alice, alice_peer = make_client(clients, 'alice')
    alice.connect_database()  # broadcasting a reply records it, as in the real loop

    alice.process_command('/rooms')

    reply = protocol.read_message(alice_peer)
    assert 'Active rooms' in reply['content']
