import socket

from server.handler import Client


def make_client(clients, nickname, room):
    server_end, _peer = socket.socketpair()
    client = Client(server_end, ('127.0.0.1', 5555), clients, lambda: False)
    client.nickname = nickname
    client.room = room
    clients.append(client)
    return client


def test_rooms_lists_active_rooms_with_counts():
    clients = []
    alice = make_client(clients, 'alice', 'general')
    make_client(clients, 'bob', 'general')
    make_client(clients, 'carol', 'games')

    assert alice.command.process(['rooms']) == 'Active rooms: games (1), general (2)'
