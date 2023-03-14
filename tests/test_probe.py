import socket

from shared.probe import probe_connection


def test_probe_succeeds_against_a_listening_socket():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    host, port = listener.getsockname()
    try:
        result = probe_connection(host, port, timeout=2.0)
    finally:
        listener.close()
    assert result.ok


def test_probe_fails_against_a_closed_port():
    # Grab a port, then immediately release it so nothing is listening there.
    spare = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    spare.bind(('127.0.0.1', 0))
    host, port = spare.getsockname()
    spare.close()

    result = probe_connection(host, port, timeout=2.0)
    assert not result.ok
    assert result.detail
