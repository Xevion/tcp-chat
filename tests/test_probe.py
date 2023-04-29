"""Probe tests against a real negotiating server.

The probe is a connect dry-run, so it is tested the same way connecting is: the
old test pointed it at a bare listening socket, which 'succeeded' on the TCP
connect alone and so never noticed that the probe had stopped speaking the
handshake. Pointing it at a real serve() closes that gap -- a TLS or version
mismatch now shows up in the probe exactly as it would on connect.
"""

import logging
import socket
import time

from client.core import probe


def _server_warnings(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def test_successful_probe_leaves_no_server_warning(boot_server, caplog):
    boot_server(56333)
    with caplog.at_level(logging.WARNING):
        result = probe('127.0.0.1', 56333, timeout=2.0)
        time.sleep(0.2)  # let the server finish handling the probe connection
    assert result.ok
    assert _server_warnings(caplog) == []  # a reachable probe is not an error


def test_mismatched_probe_does_not_warn(self_signed, boot_server, caplog):
    cert, key = self_signed
    boot_server(56335, use_tls=True, cert=cert, key=key)
    with caplog.at_level(logging.WARNING):
        result = probe('127.0.0.1', 56335, use_tls=False, timeout=2.0)
        time.sleep(0.2)
    assert not result.ok
    assert _server_warnings(caplog) == []  # a stated mismatch is a normal outcome


def test_probe_succeeds_against_a_real_server(boot_server):
    boot_server(56330)
    result = probe('127.0.0.1', 56330, timeout=2.0)
    assert result.ok


def test_probe_fails_against_a_closed_port():
    # Grab a port, then immediately release it so nothing is listening there.
    spare = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    spare.bind(('127.0.0.1', 0))
    host, port = spare.getsockname()
    spare.close()

    result = probe(host, port, timeout=2.0)
    assert not result.ok
    assert result.detail


def test_probe_without_tls_against_a_tls_server_is_rejected(self_signed, boot_server):
    cert, key = self_signed
    boot_server(56331, use_tls=True, cert=cert, key=key)
    result = probe('127.0.0.1', 56331, use_tls=False, timeout=2.0)
    assert not result.ok
    assert 'requires TLS' in result.detail


def test_probe_with_tls_against_a_plaintext_server_is_rejected(boot_server):
    boot_server(56332)
    result = probe('127.0.0.1', 56332, use_tls=True, timeout=2.0)
    assert not result.ok
    assert 'does not support TLS' in result.detail
