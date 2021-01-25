import logging
from typing import Tuple

from PyQt5.QtWidgets import QApplication

from client.dialog import ConnectionDialog
from client.gui import MainWindow

logger = logging.getLogger(__file__)


def main():
    app = QApplication([])
    app.setApplicationName("TCPChat Client")
    connect_dialog = ConnectionDialog()
    app.exec_()

    if connect_dialog.connect_pressed:
        settings = connect_dialog.settings
        m = MainWindow(settings.ip, settings.port, settings.nickname)
        app.exec_()
