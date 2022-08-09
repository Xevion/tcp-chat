from server import rooms
from shared import constants


class FakeClient:
    def __init__(self, room):
        self.room = room


def test_members_in_filters_by_room():
    a, b, c = FakeClient('general'), FakeClient('games'), FakeClient('general')
    assert rooms.members_in([a, b, c], 'general') == [a, c]
    assert rooms.members_in([a, b, c], 'games') == [b]
    assert rooms.members_in([a, b, c], 'empty') == []


def test_members_in_defaults_missing_room():
    client = object()  # no room attribute
    assert rooms.members_in([client], constants.DEFAULT_ROOM) == [client]


def test_room_counts_tallies_occupied_rooms():
    clients = [FakeClient('general'), FakeClient('general'), FakeClient('games')]
    assert rooms.room_counts(clients) == {'general': 2, 'games': 1}
