import socket

import pytest
from PyQt5.QtWidgets import QApplication

from shared import constants
from shared import protocol
from client.worker import ReceiveWorker


@pytest.fixture(scope='module')
def qapp():
    return QApplication.instance() or QApplication([])


def test_worker_replies_to_ping_with_pong(qapp):
    server_end, client_end = socket.socketpair()
    worker = ReceiveWorker(client_end, 'nick')
    worker.handle_message({'type': constants.Types.PING, 'v': 1})
    assert protocol.read_message(server_end)['type'] == constants.Types.PONG


def test_worker_answers_a_nick_request(qapp):
    server_end, client_end = socket.socketpair()
    worker = ReceiveWorker(client_end, 'zara')
    worker.handle_message({'type': constants.Types.REQUEST, 'request': constants.Requests.REQUEST_NICK})
    reply = protocol.read_message(server_end)
    assert reply['type'] == constants.Types.NICKNAME
    assert reply['nickname'] == 'zara'
