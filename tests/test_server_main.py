import socket

from shared import constants


def test_importing_server_main_does_not_bind_a_port():
    import server.main  # noqa: F401  (import is the thing under test)

    # If importing still bound the port at module level, this bind would fail.
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((constants.DEFAULT_IP, constants.DEFAULT_PORT))
    finally:
        probe.close()


def test_serve_is_callable():
    from server.main import serve
    assert callable(serve)
