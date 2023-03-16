import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt5.QtWidgets import QApplication

from server.db import ClientDatabase
from client.dialog import ConnectionDialog


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def seeded_db():
    db = ClientDatabase(':memory:')
    db.remember_connection('1.1.1.1', 5555, 'alice')
    db.remember_connection('2.2.2.2', 6000, 'bob')
    db.set_favorite('2.2.2.2', 6000, 'bob')
    return db


def test_dialog_populates_recent_and_favorites(app, seeded_db):
    dialog = ConnectionDialog(db=seeded_db)
    try:
        assert dialog.recent_connections_list.count() == 2
        assert dialog.favorite_connections_list.count() == 1
    finally:
        dialog.deleteLater()


def test_fill_from_item_copies_into_form(app, seeded_db):
    dialog = ConnectionDialog(db=seeded_db)
    try:
        # Newest first: item 0 is bob, item 1 is alice.
        dialog.fill_from_item(dialog.recent_connections_list.item(1))
        assert dialog.server_address_input.text() == '1.1.1.1'
        assert dialog.port_input.text() == '5555'
        assert dialog.nickname_input.text() == 'alice'
    finally:
        dialog.deleteLater()


def test_tls_checkbox_flows_into_settings(app, seeded_db):
    dialog = ConnectionDialog(db=seeded_db, use_tls=True)
    try:
        assert dialog.tls_checkbox.isChecked()
        assert dialog.settings.tls is True
    finally:
        dialog.deleteLater()
