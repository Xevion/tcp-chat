import re
from typing import Tuple

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QDialog, QStatusBar, QWidget, QSpacerItem, QSizePolicy

import constants
from client.ConnectionDialog import Ui_ConnectionDialog
from client.nickname import Ui_NicknameDialog
from constants import ConnectionOptions


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
        """Updates whether or not the dialog box is allowed to proceed"""
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
    def __init__(self, nickname: str = None,  *args, **kwargs):
        super(ConnectionDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.connect_button.setDisabled(True)

        if nickname:
            self.nickname_input.setText(nickname)
            self.validation()

        self.server_address_input.textEdited.connect(self.validation)
        self.port_input.textEdited.connect(self.validation)
        self.nickname_input.textEdited.connect(self.validation)
        self.connect_button.pressed.connect(self.connect)

        self.status_bar = QStatusBar(self)
        self.status_layout.addWidget(self.status_bar)

        self.connect_pressed = False

        self.show()

    def connect(self) -> None:
        self.connect_pressed = True
        self.close()

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.StatusTip:
            self.status_bar.showMessage(event.tip())
            return True
        return super().event(event)

    @property
    def settings(self) -> ConnectionOptions:
        return ConnectionOptions(ip=self.server_address_input.text() or constants.DEFAULT_IP,
                                 port=int(self.port_input.text() or constants.DEFAULT_PORT),
                                 nickname=self.nickname_input.text(),
                                 password=self.password_input.text(),
                                 remember=self.remember_checkbox.checkState())

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
            self.status_bar.showMessage('Please use a valid nickname. Letters and digits, 3-15 characters long.', 3000)

        self.connect_button.setDisabled(not (address and port and nickname))
        self.test_connection_button.setDisabled(not (address and port))

    def validate_nickname(self) -> bool:
        """Returns True if the nickname follows the nickname guidelines requested."""
        return re.match(r'^[A-z0-9]{3,15}$', self.nickname_input.text()) is not None

    def validate_address(self) -> Tuple[bool, bool]:
        """Returns True if the server address and port combination is valid"""
        address = self.server_address_input.text() or constants.DEFAULT_IP
        port = self.port_input.text() or str(constants.DEFAULT_PORT)

        valid_address = len(address) > 0 and re.match(r'^\d{1,4}\.\d{1,4}\.\d{1,4}\.\d{1,4}|localhost$',
                                                      address) is not None
        valid_port = len(port) > 0 and re.match(r'^\d{4,5}$', port) is not None and 1024 <= int(port) <= 65536

        return valid_address, valid_port
