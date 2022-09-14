"""Exponential backoff delays for retrying a dropped connection."""

from typing import Iterator


def backoff_delays(base: float = 1.0, factor: float = 2.0, maximum: float = 30.0) -> Iterator[float]:
    """Yield an endless run of delays that grow by ``factor`` each step, capped at ``maximum``.

    With the defaults this gives 1, 2, 4, 8, 16, 30, 30, ... seconds, so a client
    retries quickly at first and then settles into a steady polling interval.
    """
    delay = base
    while True:
        yield min(delay, maximum)
        delay *= factor
