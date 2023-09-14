import shutil
import socket
import subprocess
import threading

import pytest

from shared import protocol
from shared import tls


@pytest.fixture
def self_signed(tmp_path):
    openssl = shutil.which('openssl')
    if openssl is None:
        pytest.skip('openssl is not available to generate a test certificate')
    cert, key = tmp_path / 'cert.pem', tmp_path / 'key.pem'
    subprocess.run(
        [
            openssl,
            'req',
            '-x509',
            '-newkey',
            'rsa:2048',
            '-nodes',
            '-keyout',
            str(key),
            '-out',
            str(cert),
            '-days',
            '1',
            '-subj',
            '/CN=localhost',
        ],
        check=True,
        capture_output=True,
    )
    return str(cert), str(key)


def test_tls_round_trip_over_protocol_framing(self_signed):
    cert, key = self_signed
    server_ctx = tls.server_context(cert, key)
    client_ctx = tls.client_context(verify=False)

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    listener.settimeout(5)
    host, port = listener.getsockname()

    received = {}

    def serve():
        raw, _ = listener.accept()
        conn = server_ctx.wrap_socket(raw, server_side=True)
        received['message'] = protocol.read_message(conn)
        conn.sendall(protocol.encode({'type': 'MESSAGE', 'content': 'pong'}))
        conn.close()

    server_thread = threading.Thread(target=serve)
    server_thread.start()
    try:
        client = client_ctx.wrap_socket(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname='localhost'
        )
        client.connect((host, port))
        client.sendall(protocol.encode({'type': 'MESSAGE', 'content': 'ping'}))
        reply = protocol.read_message(client)
        client.close()
    finally:
        server_thread.join(5)
        listener.close()

    assert received['message']['content'] == 'ping'
    assert reply['content'] == 'pong'
