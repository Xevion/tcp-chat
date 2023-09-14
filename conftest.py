import os
import shutil
import socket
import subprocess
import sys
import threading
import time

import pytest

# Ensure the project root is importable when running the test suite directly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _wait_until_listening(host, port, deadline=5.0):
    end = time.time() + deadline
    while time.time() < end:
        try:
            socket.create_connection((host, port), timeout=0.5).close()
            return
        except OSError:
            time.sleep(0.05)
    raise AssertionError(f'server never came up on {host}:{port}')


@pytest.fixture
def boot_server(monkeypatch):
    """Start a real serve() on a daemon thread and wait until it is listening.

    Returns a factory so a test can boot one (optionally TLS) and then drive it
    over real sockets -- the connection logic the UI actually runs, exercised
    headless rather than faked one side at a time.
    """
    from shared import constants

    def _boot(port, use_tls=False, cert=None, key=None):
        if use_tls:
            monkeypatch.setattr(constants, 'TLS_CERT', cert)
            monkeypatch.setattr(constants, 'TLS_KEY', key)
        from server.main import serve

        thread = threading.Thread(
            target=serve,
            kwargs={'host': '127.0.0.1', 'port': port, 'use_tls': use_tls},
            daemon=True,
        )
        thread.start()
        _wait_until_listening('127.0.0.1', port)
        return thread

    return _boot


@pytest.fixture
def self_signed(tmp_path):
    """Generate a throwaway self-signed cert/key pair, skipping if openssl is absent."""
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
