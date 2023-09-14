"""Headless smoke tests for the thin Qt view against a real server.

The window is exercised offscreen over an actual serve(), so these check the
view's own job -- rendering core events and surviving a failed connect -- on the
same connection logic the core tests cover. Anything that breaks here is a UI
handling bug, not a connection bug, which keeps them easy to read.
"""

import os
import socket
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt5.QtWidgets import QApplication

from client.gui import MainWindow


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def _pump(app, predicate, timeout=4.0):
    """Spin the Qt event loop until predicate() holds or the timeout elapses."""
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.02)
    return False


def _close(window):
    window.close()
    window.receiveThread.wait(2000)  # let the worker thread unwind cleanly


def test_failed_connect_raises_instead_of_crashing(app):
    # Reserve a port and release it so the connect is refused.
    spare = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    spare.bind(('127.0.0.1', 0))
    host, port = spare.getsockname()
    spare.close()

    # A refused connection must be a catchable error (the caller re-prompts),
    # not an unhandled exception that takes the app down.
    with pytest.raises(ConnectionError):
        MainWindow(host, port, 'alice')


def _user_names(window):
    return [window.connectionsList.item(i).text() for i in range(window.connectionsList.count())]


def test_window_renders_the_user_list_from_the_server(app, boot_server):
    boot_server(56430)
    window = MainWindow('127.0.0.1', 56430, 'alice')
    try:
        # The nickname round-trip lands a user list that includes us.
        assert _pump(app, lambda: 'alice' in _user_names(window))
    finally:
        _close(window)


def test_window_shows_a_message_it_sends(app, boot_server):
    boot_server(56431)
    window = MainWindow('127.0.0.1', 56431, 'alice')
    try:
        # Wait until the nickname round-trip has registered us on the server.
        assert _pump(app, lambda: 'alice' in _user_names(window))
        window.send_message('hello world')
        assert _pump(app, lambda: any(m.get('message') == 'hello world' for m in window.messages))
    finally:
        _close(window)
