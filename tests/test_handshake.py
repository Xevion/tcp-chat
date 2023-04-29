import shutil
import socket
import ssl
import subprocess
import threading

import pytest

from shared import handshake
from shared import protocol


def _run_server(target):
    """Run a negotiation server callable in a thread, returning its result dict."""
    box = {}

    def runner():
        box['result'] = target()

    thread = threading.Thread(target=runner)
    thread.start()
    return thread, box


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


def test_plaintext_negotiation_succeeds():
    a, b = socket.socketpair()
    thread, box = _run_server(
        lambda: handshake.negotiate_server(a, require_tls=False, supports_tls=False, version=1))
    client = handshake.negotiate_client(b, want_tls=False, version=1)
    thread.join()

    assert client.ok
    assert box['result'].ok


def test_server_requiring_tls_rejects_a_plaintext_client():
    a, b = socket.socketpair()
    thread, box = _run_server(
        lambda: handshake.negotiate_server(a, require_tls=True, supports_tls=True, version=1))
    client = handshake.negotiate_client(b, want_tls=False, version=1)
    thread.join()

    assert not client.ok
    assert 'TLS' in client.reason
    assert not box['result'].ok


def test_client_wanting_tls_against_a_plaintext_server_is_rejected():
    a, b = socket.socketpair()
    thread, box = _run_server(
        lambda: handshake.negotiate_server(a, require_tls=False, supports_tls=False, version=1))
    client = handshake.negotiate_client(b, want_tls=True, version=1)
    thread.join()

    assert not client.ok
    assert 'TLS' in client.reason


def test_version_mismatch_is_rejected():
    a, b = socket.socketpair()
    thread, box = _run_server(
        lambda: handshake.negotiate_server(a, require_tls=False, supports_tls=False, version=2))
    client = handshake.negotiate_client(b, want_tls=False, version=1)
    thread.join()

    assert not client.ok
    assert 'version' in client.reason.lower()


def test_a_server_rejection_is_marked_permanent():
    a, b = socket.socketpair()
    thread, box = _run_server(
        lambda: handshake.negotiate_server(a, require_tls=True, supports_tls=True, version=1))
    client = handshake.negotiate_client(b, want_tls=False, version=1)
    thread.join()

    assert not client.ok
    assert client.rejected is True  # the server stated a refusal; retrying won't help


def test_a_transport_failure_is_not_marked_permanent():
    a, b = socket.socketpair()
    a.close()  # the other end vanishes mid-handshake
    client = handshake.negotiate_client(b, want_tls=False, version=1)

    assert not client.ok
    assert client.rejected is False  # a dropped link might recover; safe to retry


def test_a_probe_hello_is_reported_to_the_server():
    a, b = socket.socketpair()
    thread, box = _run_server(
        lambda: handshake.negotiate_server(a, require_tls=False, supports_tls=False, version=1))
    client = handshake.negotiate_client(b, want_tls=False, version=1, is_probe=True)
    thread.join()

    assert client.ok
    assert box['result'].ok
    assert box['result'].probe is True  # so the server can answer and hang up cleanly


def test_a_normal_hello_is_not_flagged_as_a_probe():
    a, b = socket.socketpair()
    thread, box = _run_server(
        lambda: handshake.negotiate_server(a, require_tls=False, supports_tls=False, version=1))
    handshake.negotiate_client(b, want_tls=False, version=1)
    thread.join()

    assert box['result'].probe is False


def test_tls_negotiation_upgrades_both_ends(self_signed):
    cert, key = self_signed
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    host, port = listener.getsockname()

    box = {}

    def server():
        raw, _ = listener.accept()
        result = handshake.negotiate_server(raw, require_tls=True, supports_tls=True,
                                            version=1, certfile=cert, keyfile=key)
        box['result'] = result
        box['message'] = protocol.read_message(result.sock)

    thread = threading.Thread(target=server)
    thread.start()
    try:
        raw = socket.create_connection((host, port))
        client = handshake.negotiate_client(raw, want_tls=True, version=1,
                                            verify=False, server_hostname='localhost')
        client.sock.sendall(protocol.encode({'type': 'MESSAGE', 'content': 'secret'}))
    finally:
        thread.join(5)
        listener.close()

    assert client.ok and box['result'].ok
    assert box['message']['content'] == 'secret'
    assert isinstance(client.sock, ssl.SSLSocket)  # the channel was really upgraded
