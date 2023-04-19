import socket
import threading

from client import gui
from client.gui import MainWindow
from shared import handshake
from shared import protocol
from shared.backoff import backoff_delays


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

    # open_socket now runs the handshake, so the peer has to answer it.
    def accept_and_negotiate():
        raw, _ = listener.accept()
        handshake.negotiate_server(raw, require_tls=False, supports_tls=False,
                                   version=protocol.PROTOCOL_VERSION)

    thread = threading.Thread(target=accept_and_negotiate)
    thread.start()
    try:
        window = bare_window(ip, port)
        assert window.open_socket() is True
        window.client.close()
    finally:
        thread.join(5)
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


def test_a_permanent_rejection_stops_reconnecting(monkeypatch):
    scheduled = []
    monkeypatch.setattr(gui.QTimer, 'singleShot',
                        staticmethod(lambda ms, fn: scheduled.append(ms)))

    window = MainWindow.__new__(MainWindow)
    window.closed = False
    window._reconnect_delays = backoff_delays()
    window.status_bar = _StubStatusBar()
    # The connect attempt fails for a stated reason that won't fix itself.
    window._connect_permanent = True
    window._connect_reason = 'server requires TLS'
    window.open_socket = lambda: False

    window.try_reconnect()
    assert scheduled == []  # no further attempts scheduled


def test_a_transient_failure_keeps_retrying(monkeypatch):
    scheduled = []
    monkeypatch.setattr(gui.QTimer, 'singleShot',
                        staticmethod(lambda ms, fn: scheduled.append(ms)))

    window = MainWindow.__new__(MainWindow)
    window.closed = False
    window._reconnect_delays = backoff_delays()
    window.status_bar = _StubStatusBar()
    window._connect_permanent = False
    window._connect_reason = ''
    window.open_socket = lambda: False

    window.try_reconnect()
    assert len(scheduled) == 1  # scheduled another attempt
