import shutil
import socket
import subprocess
import threading
import time

import pytest

from shared import constants
from shared import protocol
from shared import tls


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


@pytest.fixture
def self_signed(tmp_path):
    openssl = shutil.which('openssl')
    if openssl is None:
        pytest.skip('openssl is not available to generate a test certificate')
    cert, key = tmp_path / 'cert.pem', tmp_path / 'key.pem'
    subprocess.run(
        [openssl, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
         '-keyout', str(key), '-out', str(cert), '-days', '1', '-subj', '/CN=localhost'],
        check=True, capture_output=True,
    )
    return str(cert), str(key)


def _wait_until_listening(host, port, deadline=5.0):
    end = time.time() + deadline
    while time.time() < end:
        try:
            socket.create_connection((host, port), timeout=0.5).close()
            return
        except OSError:
            time.sleep(0.05)
    raise AssertionError(f'server never came up on {host}:{port}')


def test_serve_survives_a_bad_handshake(self_signed, monkeypatch):
    from server.main import serve

    cert, key = self_signed
    monkeypatch.setattr(constants, 'TLS_CERT', cert)
    monkeypatch.setattr(constants, 'TLS_KEY', key)

    host, port = '127.0.0.1', 55733
    thread = threading.Thread(target=serve, kwargs={'host': host, 'port': port, 'use_tls': True},
                              daemon=True)
    thread.start()
    _wait_until_listening(host, port)

    # A plaintext client against the TLS listener fails the handshake server-side.
    bad = socket.create_connection((host, port))
    bad.sendall(b'not a tls hello\n')
    bad.close()
    time.sleep(0.2)

    # The server must still be alive and serving a proper TLS client.
    client = tls.client_context(verify=False).wrap_socket(
        socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname='localhost')
    client.connect((host, port))
    client.settimeout(5)
    message = protocol.read_message(client)
    client.close()

    assert thread.is_alive()
    assert message['type'] == constants.Types.REQUEST
