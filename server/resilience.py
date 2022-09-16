"""Timing helpers for the server's keep-alive heartbeat.

Kept as small pure functions so the heartbeat policy can be reasoned about and
tested without sockets or threads.
"""


def is_stale(last_seen: float, now: float, timeout: float) -> bool:
    """True once nothing has been heard from a client for longer than ``timeout``."""
    return (now - last_seen) > timeout


def should_ping(last_seen: float, last_ping: float, now: float, interval: float) -> bool:
    """True when a client has gone quiet for ``interval`` and isn't already being probed."""
    return (now - last_seen) >= interval and (now - last_ping) >= interval
