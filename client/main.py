import logging

from PyQt5.QtWidgets import QApplication

from client.dialog import ConnectionDialog
from client.gui import MainWindow
from client import theme

logger = logging.getLogger(__file__)


def main(nickname: str = None):
    app = QApplication([])
    app.setApplicationName("TCPChat Client")
    app.setStyleSheet(theme.DARK_STYLESHEET)
    connect_dialog = ConnectionDialog(nickname=nickname)
    app.exec_()

    if connect_dialog.connect_pressed:
        settings = connect_dialog.settings
        window = MainWindow(settings.ip, settings.port, settings.nickname)
        app.exec_()
