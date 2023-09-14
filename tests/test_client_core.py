"""Headless tests for the Qt-free client core, driven over real sockets.

These boot an actual ``serve()`` and run the exact connection/receive logic the
GUI uses -- so the core the UI runs and the core the tests exercise are the same
object, and a connection bug shows up here instead of only in manual play.
"""

import socket

import pytest

from shared import constants
from shared import protocol
from client import core


def test_core_replies_to_ping_with_pong():
    server_end, client_end = socket.socketpair()
    c = core.ClientCore('host', 1, 'nick')
    c.sock = client_end
    list(c._dispatch({'type': constants.Types.PING}))  # control frames yield no event
    assert protocol.read_message(server_end)['type'] == constants.Types.PONG


def test_core_answers_a_nick_request():
    server_end, client_end = socket.socketpair()
    c = core.ClientCore('host', 1, 'zara')
    c.sock = client_end
    list(c._dispatch({'type': constants.Types.REQUEST, 'request': constants.Requests.REQUEST_NICK}))
    reply = protocol.read_message(server_end)
    assert reply['type'] == constants.Types.NICKNAME
    assert reply['nickname'] == 'zara'


def test_connect_failure_is_reported_not_raised():
    # Reserve a port and release it so nothing is listening there.
    spare = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    spare.bind(('127.0.0.1', 0))
    host, port = spare.getsockname()
    spare.close()

    c = core.ClientCore(host, port, 'alice')
    result = c.connect()
    assert not result.ok
    assert not result.permanent  # a refused connection is transient, worth retrying
    assert result.reason


def test_connect_to_tls_server_without_tls_is_permanent(self_signed, boot_server):
    cert, key = self_signed
    boot_server(56231, use_tls=True, cert=cert, key=key)

    c = core.ClientCore('127.0.0.1', 56231, 'alice', use_tls=False)
    result = c.connect()
    assert not result.ok
    assert result.permanent  # the server stated a refusal; retrying can't fix it
    assert 'requires TLS' in result.reason


def test_connect_then_receives_user_list_with_our_nickname(boot_server):
    boot_server(56232)

    c = core.ClientCore('127.0.0.1', 56232, 'alice')
    assert c.connect().ok
    c.sock.settimeout(3.0)  # bound the test if the expected event never arrives
    try:
        for event in c.events():
            if event.type == core.USER_LIST and 'alice' in {
                u['nickname'] for u in event.payload['users']
            }:
                break
            if event.type == core.DISCONNECTED:
                pytest.fail('disconnected before the user list arrived')
    finally:
        c.close()


def test_sent_message_is_broadcast_back(boot_server):
    boot_server(56233)

    c = core.ClientCore('127.0.0.1', 56233, 'alice')
    assert c.connect().ok
    c.sock.settimeout(3.0)
    sent = False
    try:
        for event in c.events():
            if (
                event.type == core.USER_LIST
                and not sent
                and 'alice' in {u['nickname'] for u in event.payload['users']}
            ):
                c.send_message('hello')
                sent = True
            elif event.type == core.MESSAGE and event.payload['message'] == 'hello':
                assert event.payload['nickname'] == 'alice'
                break
            elif event.type == core.DISCONNECTED:
                pytest.fail('disconnected before the message echoed back')
    finally:
        c.close()


def test_backoff_advances_and_resets():
    c = core.ClientCore('127.0.0.1', 1, 'alice')
    first = c.next_reconnect_delay()
    second = c.next_reconnect_delay()
    assert second >= first

    c.reset_backoff()
    assert c.next_reconnect_delay() <= first  # a fresh sequence starts over
