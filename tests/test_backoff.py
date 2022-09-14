import itertools

from shared.backoff import backoff_delays


def test_backoff_grows_and_caps():
    delays = list(itertools.islice(backoff_delays(base=1, factor=2, maximum=30), 8))
    assert delays == [1, 2, 4, 8, 16, 30, 30, 30]


def test_backoff_honours_a_custom_base():
    delays = list(itertools.islice(backoff_delays(base=0.5, factor=3, maximum=10), 5))
    assert delays == [0.5, 1.5, 4.5, 10, 10]
