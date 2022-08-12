import socket

from shared import constants
from shared import protocol
from server.handler import Client


class FakeDB:
    def add_message(self, *args):
        return 1


def make_client(clients, nickname, room=constants.DEFAULT_ROOM):
    server_end, peer = socket.socketpair()
    client = Client(server_end, ('127.0.0.1', 5555), clients, lambda: False)
    client.nickname = nickname
    client.room = room
    client.db = FakeDB()
    clients.append(client)
    return client, peer


def test_join_moves_client_to_the_new_room():
    clients = []
    alice, _ = make_client(clients, 'alice')
    alice.command.process(['join', 'games'])
    assert alice.room == 'games'


def test_join_announces_departure_to_the_old_room():
    clients = []
    alice, _ = make_client(clients, 'alice')
    bob, bob_peer = make_client(clients, 'bob')
    bob_peer.settimeout(0.5)

    alice.command.process(['join', 'games'])

    departure = protocol.read_message(bob_peer)
    assert departure['type'] == constants.Types.MESSAGE
    assert 'left for games' in departure['content']
    # Following the announcement, bob's room list no longer includes alice.
    user_list = protocol.read_message(bob_peer)
    assert {user['nickname'] for user in user_list['users']} == {'bob'}


def test_join_rejects_the_current_room():
    clients = []
    alice, _ = make_client(clients, 'alice', room='general')
    assert alice.command.process(['join', 'general']) == 'You are already in general.'
    assert alice.command.process(['join']) == 'Usage: /join <room>'
