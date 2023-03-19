import socket

from client import gui
from client.gui import MainWindow


class _StubStatusBar:
    def showMessage(self, *args, **kwargs):
        pass


def bare_window(ip, port):
    # Bypass __init__ so we can exercise open_socket without a Qt event loop.
    window = MainWindow.__new__(MainWindow)
    window.ip, window.port = ip, port
    window.use_tls = False
    return window


def test_open_socket_succeeds_against_a_listener():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    ip, port = listener.getsockname()
    try:
        window = bare_window(ip, port)
        assert window.open_socket() is True
        window.client.close()
    finally:
        listener.close()


def test_open_socket_fails_when_nothing_listens():
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(('127.0.0.1', 0))
    ip, port = probe.getsockname()
    probe.close()  # port is now free, so a connect should be refused
    window = bare_window(ip, port)
    assert window.open_socket() is False


def test_repeated_losses_back_off_instead_of_hot_looping(monkeypatch):
    scheduled = []
    monkeypatch.setattr(gui.QTimer, 'singleShot',
                        staticmethod(lambda ms, fn: scheduled.append(ms)))

    window = MainWindow.__new__(MainWindow)
    window.closed = False
    window._reconnect_delays = None
    window._stability_timer = None
    window.status_bar = _StubStatusBar()

    # Three drops in a row, before any reconnect can prove itself stable.
    window.on_connection_lost()
    window.on_connection_lost()
    window.on_connection_lost()

    # Delays must grow, never stay pinned at zero (which would spin the CPU).
    assert scheduled == sorted(scheduled)
    assert scheduled[0] > 0
    assert scheduled[-1] > scheduled[0]


def test_a_stable_connection_resets_the_backoff():
    window = MainWindow.__new__(MainWindow)
    window._reconnect_delays = object()  # pretend a backoff is in progress
    window._mark_connection_stable()
    assert window._reconnect_delays is None
