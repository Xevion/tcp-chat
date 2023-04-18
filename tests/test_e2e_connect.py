"""End-to-end connect matrix against a real server over real sockets.

This is the structural net for the whole connection-failure family: it boots an
actual ``serve()`` and drives the real client negotiation across every TLS /
version combination, so a mismatch that unit tests can't see (because they fake
one side) shows up here as a failing assertion.
"""

import socket
import threading
import time

import pytest

from shared import constants
from shared import handshake
from shared import protocol

VERSION = protocol.PROTOCOL_VERSION


def _start_server(port, use_tls, cert=None, key=None, monkeypatch=None):
    if use_tls:
        monkeypatch.setattr(constants, 'TLS_CERT', cert)
        monkeypatch.setattr(constants, 'TLS_KEY', key)
    from server.main import serve
    thread = threading.Thread(target=serve,
                              kwargs={'host': '127.0.0.1', 'port': port, 'use_tls': use_tls},
                              daemon=True)
    thread.start()
    _wait_until_listening('127.0.0.1', port)
    return thread


def _wait_until_listening(host, port, deadline=5.0):
    end = time.time() + deadline
    while time.time() < end:
        try:
            socket.create_connection((host, port), timeout=0.5).close()
            return
        except OSError:
            time.sleep(0.05)
    raise AssertionError(f'server never came up on {host}:{port}')


def _connect(port, want_tls, version=VERSION):
    raw = socket.create_connection(('127.0.0.1', port))
    return handshake.negotiate_client(raw, want_tls=want_tls, version=version,
                                      verify=False, server_hostname='localhost')


def test_plaintext_client_to_plaintext_server_connects():
    _start_server(56120, use_tls=False)
    result = _connect(56120, want_tls=False)
    assert result.ok
    assert protocol.read_message(result.sock)['type'] == constants.Types.REQUEST


def test_tls_client_to_tls_server_connects(self_signed, monkeypatch):
    cert, key = self_signed
    _start_server(56121, use_tls=True, cert=cert, key=key, monkeypatch=monkeypatch)
    result = _connect(56121, want_tls=True)
    assert result.ok
    assert protocol.read_message(result.sock)['type'] == constants.Types.REQUEST


def test_plaintext_client_to_tls_server_is_rejected(self_signed, monkeypatch):
    cert, key = self_signed
    _start_server(56122, use_tls=True, cert=cert, key=key, monkeypatch=monkeypatch)
    result = _connect(56122, want_tls=False)
    assert not result.ok
    assert 'requires TLS' in result.reason


def test_tls_client_to_plaintext_server_is_rejected():
    _start_server(56123, use_tls=False)
    result = _connect(56123, want_tls=True)
    assert not result.ok
    assert 'does not support TLS' in result.reason


def test_version_skew_is_rejected():
    _start_server(56124, use_tls=False)
    result = _connect(56124, want_tls=False, version=VERSION + 999)
    assert not result.ok
    assert 'version' in result.reason.lower()
