"""The thin reconnect glue in MainWindow, over a fake core.

The connection logic itself (connecting, the backoff sequence, permanent vs
transient classification) lives in the core and is covered headless in
test_client_core.py. These tests only check that the window drives that core
correctly: schedules a retry on a drop, gives up on a stated rejection, and
resets the backoff once a link proves stable.
"""

from client import gui
from client.gui import MainWindow
from client.core import ConnectResult


class _StubStatusBar:
    def showMessage(self, *args, **kwargs):
        pass


class _FakeCore:
    def __init__(self, result=None, delays=(1.0, 2.0, 4.0)):
        self._delays = iter(delays)
        self._result = result
        self.reset_called = False

    def next_reconnect_delay(self):
        return next(self._delays)

    def reset_backoff(self):
        self.reset_called = True

    def connect(self):
        return self._result


def _bare_window(core):
    # Bypass __init__ so we can exercise the glue without a Qt event loop.
    window = MainWindow.__new__(MainWindow)
    window.closed = False
    window._stability_timer = None
    window.status_bar = _StubStatusBar()
    window.core = core
    return window


def test_repeated_losses_back_off_instead_of_hot_looping(monkeypatch):
    scheduled = []
    monkeypatch.setattr(gui.QTimer, 'singleShot',
                        staticmethod(lambda ms, fn: scheduled.append(ms)))
    window = _bare_window(_FakeCore())

    # Three drops in a row, before any reconnect can prove itself stable.
    window.on_connection_lost()
    window.on_connection_lost()
    window.on_connection_lost()

    # Delays must grow, never stay pinned at zero (which would spin the CPU).
    assert scheduled == sorted(scheduled)
    assert scheduled[0] > 0
    assert scheduled[-1] > scheduled[0]


def test_a_stable_connection_resets_the_backoff():
    core = _FakeCore()
    window = _bare_window(core)
    window._mark_connection_stable()
    assert core.reset_called


def test_a_permanent_rejection_stops_reconnecting(monkeypatch):
    scheduled = []
    monkeypatch.setattr(gui.QTimer, 'singleShot',
                        staticmethod(lambda ms, fn: scheduled.append(ms)))
    core = _FakeCore(result=ConnectResult(False, None, 'server requires TLS', permanent=True))
    window = _bare_window(core)

    window.try_reconnect()
    assert scheduled == []  # no further attempts scheduled


def test_a_transient_failure_keeps_retrying(monkeypatch):
    scheduled = []
    monkeypatch.setattr(gui.QTimer, 'singleShot',
                        staticmethod(lambda ms, fn: scheduled.append(ms)))
    core = _FakeCore(result=ConnectResult(False, None, 'connection refused', permanent=False))
    window = _bare_window(core)

    window.try_reconnect()
    assert len(scheduled) == 1  # scheduled another attempt
