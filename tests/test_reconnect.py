import socket

from client.gui import MainWindow


def bare_window(ip, port):
    # Bypass __init__ so we can exercise open_socket without a Qt event loop.
    window = MainWindow.__new__(MainWindow)
    window.ip, window.port = ip, port
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
