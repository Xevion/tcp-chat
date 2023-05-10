"""Helpers for grouping connected clients into named rooms.

Rooms are derived from each client's ``room`` attribute rather than a separate
registry, so a client can only ever be in one room and membership can't drift
out of sync with the connection list.
"""

from typing import Dict, List

from shared import constants


def members_in(clients, room: str) -> List:
    """Return the connected clients currently in ``room``."""
    return [client for client in clients if getattr(client, 'room', constants.DEFAULT_ROOM) == room]


def room_counts(clients) -> Dict[str, int]:
    """Return a mapping of room name to member count for every occupied room."""
    counts: Dict[str, int] = {}
    for client in clients:
        room = getattr(client, 'room', constants.DEFAULT_ROOM)
        counts[room] = counts.get(room, 0) + 1
    return counts
