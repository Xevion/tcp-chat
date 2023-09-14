import re
from typing import Optional, Tuple

from PyQt5.QtCore import QEvent, Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog, QStatusBar, QListWidgetItem, QMenu

from shared.constants import ConnectionOptions, DEFAULT_IP, DEFAULT_PORT
from client.core import probe
from server.db import ClientDatabase
from client.ui.ConnectionDialog import Ui_ConnectionDialog
from client.nickname import Ui_NicknameDialog


class ProbeWorker(QThread):
    """Run a reachability probe off the UI thread and report the outcome."""

    result = pyqtSignal(bool, str)

    def __init__(self, host: str, port: int, use_tls: bool, parent=None):
        super().__init__(parent)
        self.host, self.port, self.use_tls = host, port, use_tls

    def run(self):
        outcome = probe(self.host, self.port, use_tls=self.use_tls)
        self.result.emit(outcome.ok, outcome.detail)


class NicknameDialog(QDialog, Ui_NicknameDialog):
    def __init__(self, *args, **kwargs):
        super(NicknameDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.disabled = True
        self.buttonBox.setDisabled(True)

        self.setWindowTitle("Set Nickname")

        self.lineEdit.returnPressed.connect(self.trySubmit)
        self.lineEdit.textEdited.connect(self.controlSubmit)
        self.show()

    def controlSubmit(self):
        """Updates whether the dialog box is allowed to proceed"""
        if len(self.lineEdit.text()) > 2:
            if self.disabled:
                self.disabled = False
                self.buttonBox.setDisabled(False)
        else:
            if not self.disabled:
                self.disabled = True
                self.buttonBox.setDisabled(True)

    def trySubmit(self):
        """Tries to submit the Dialog through the QLineEdit via Enter key"""
        if not self.disabled:
            self.accept()


class ConnectionDialog(QDialog, Ui_ConnectionDialog):
    def __init__(
        self,
        nickname: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        use_tls: bool = False,
        db: Optional[ClientDatabase] = None,
        *args,
        **kwargs,
    ):
        super(ConnectionDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.connect_button.setDisabled(True)
        self.test_connection_button.setDisabled(True)
        self.tls_checkbox.setChecked(bool(use_tls))

        # Prefill with the last connection the user made, if any.
        self.db = db if db is not None else ClientDatabase()
        last = self.db.last_connection()
        if last is not None:
            self.server_address_input.setText(last['address'])
            self.port_input.setText(str(last['port']))
            if not nickname:
                nickname = last['nickname']

        # CLI/config values override the remembered connection.
        if host is not None:
            self.server_address_input.setText(host)
        if port is not None:
            self.port_input.setText(str(port))

        if nickname:
            self.nickname_input.setText(nickname)
            self.validation()

        self.server_address_input.textEdited.connect(self.validation)
        self.port_input.textEdited.connect(self.validation)
        self.nickname_input.textEdited.connect(self.validation)
        self.connect_button.pressed.connect(self.connect)
        self.test_connection_button.pressed.connect(self.test_connection)

        # Click a saved server to fill the form; right-click a recent one to (un)favorite.
        self.recent_connections_list.itemClicked.connect(self.fill_from_item)
        self.favorite_connections_list.itemClicked.connect(self.fill_from_item)
        self.recent_connections_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recent_connections_list.customContextMenuRequested.connect(self.show_recent_menu)

        self.status_bar = QStatusBar(self)
        self.status_layout.addWidget(self.status_bar)

        self.connect_pressed = False
        self._probe: Optional[ProbeWorker] = None

        self.load_connection_lists()
        self.show()

    def connect(self) -> None:
        self.connect_pressed = True
        settings = self.settings
        if settings.remember:
            self.db.remember_connection(
                settings.ip, settings.port, settings.nickname, settings.password or None
            )
        else:
            self.db.remember_connection(settings.ip, settings.port, settings.nickname)
        self.close()

    def load_connection_lists(self) -> None:
        """(Re)populate the Recent and Favorites tabs from the database."""
        self.recent_connections_list.clear()
        for conn in self.db.recent_connections():
            self._add_connection_item(self.recent_connections_list, conn)

        self.favorite_connections_list.clear()
        for conn in self.db.favorite_connections():
            self._add_connection_item(self.favorite_connections_list, conn)

    @staticmethod
    def _add_connection_item(list_widget, conn: dict) -> None:
        star = '★ ' if conn['favorite'] else ''
        item = QListWidgetItem(f"{star}{conn['nickname']}@{conn['address']}:{conn['port']}")
        item.setData(Qt.UserRole, conn)
        list_widget.addItem(item)

    def fill_from_item(self, item: QListWidgetItem) -> None:
        """Drop a saved connection's details into the form fields."""
        conn = item.data(Qt.UserRole)
        self.server_address_input.setText(conn['address'])
        self.port_input.setText(str(conn['port']))
        self.nickname_input.setText(conn['nickname'])
        self.validation()

    def show_recent_menu(self, point) -> None:
        item = self.recent_connections_list.itemAt(point)
        if item is None:
            return
        conn = item.data(Qt.UserRole)
        menu = QMenu(self)
        action = menu.addAction('Remove favorite' if conn['favorite'] else 'Add favorite')
        if menu.exec_(self.recent_connections_list.mapToGlobal(point)) == action:
            self.db.set_favorite(
                conn['address'], conn['port'], conn['nickname'], favorite=not conn['favorite']
            )
            self.load_connection_lists()

    def test_connection(self) -> None:
        """Fire a quick reachability probe and report the result in the status bar."""
        address, port = self.validate_address()
        if not (address and port):
            self.status_bar.showMessage('Enter a valid address and port first.', 3000)
            return
        self.test_connection_button.setDisabled(True)  # throttle to one probe at a time
        self.status_bar.showMessage('Testing connection...')
        settings = self.settings
        self._probe = ProbeWorker(settings.ip, settings.port, settings.tls, self)
        self._probe.result.connect(self.on_probe_result)
        self._probe.start()

    def on_probe_result(self, ok: bool, detail: str) -> None:
        self.status_bar.showMessage(detail, 5000)
        address, port = self.validate_address()
        self.test_connection_button.setDisabled(not (address and port))

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.StatusTip:
            self.status_bar.showMessage(event.tip())
            return True
        return super().event(event)

    @property
    def settings(self) -> ConnectionOptions:
        return ConnectionOptions(
            ip=self.server_address_input.text() or DEFAULT_IP,
            port=int(self.port_input.text() or DEFAULT_PORT),
            nickname=self.nickname_input.text(),
            password=self.password_input.text(),
            remember=self.remember_checkbox.checkState(),
            tls=self.tls_checkbox.isChecked(),
        )

    def validation(self, full: bool = True) -> None:
        address, port = self.validate_address()
        nickname = self.validate_nickname()

        if not address and not port:
            self.status_bar.showMessage('Please fill in a valid server address and port.', 3000)
        elif not address:
            self.status_bar.showMessage('Please fill in a valid server address.', 3000)
        elif not port:
            self.status_bar.showMessage('Please fill in a valid port number.', 3000)
        elif full and not nickname:
            self.status_bar.showMessage(
                'Please use a valid nickname. Letters and digits, 3-15 characters long.', 3000
            )

        self.connect_button.setDisabled(not (address and port and nickname))
        self.test_connection_button.setDisabled(not (address and port))

    def validate_nickname(self) -> bool:
        """Returns True if the nickname follows the nickname guidelines requested."""
        return re.match(r'^[A-z0-9]{3,15}$', self.nickname_input.text()) is not None

    def validate_address(self) -> Tuple[bool, bool]:
        """Returns True if the server address and port combination is valid"""
        address = self.server_address_input.text() or DEFAULT_IP
        port = self.port_input.text() or str(DEFAULT_PORT)

        valid_address = (
            len(address) > 0
            and re.match(r'^\d{1,4}\.\d{1,4}\.\d{1,4}\.\d{1,4}|localhost$', address) is not None
        )
        valid_port = (
            len(port) > 0
            and re.match(r'^\d{4,5}$', port) is not None
            and 1024 <= int(port) <= 65536
        )

        return valid_address, valid_port
