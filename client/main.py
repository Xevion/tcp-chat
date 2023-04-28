import logging

from PyQt5.QtWidgets import QApplication, QMessageBox

from client.dialog import ConnectionDialog
from client.gui import MainWindow
from client import theme

logger = logging.getLogger(__name__)


def main(nickname: str = None, host: str = None, port: int = None, use_tls: bool = None):
    app = QApplication([])
    app.setApplicationName("TCPChat Client")
    app.setStyleSheet(theme.DARK_STYLESHEET)

    # Loop the connection dialog so a failed connection re-prompts instead of
    # crashing out of the application with an unhandled error.
    while True:
        dialog = ConnectionDialog(nickname=nickname, host=host, port=port, use_tls=bool(use_tls))
        app.exec_()
        if not dialog.connect_pressed:
            return  # user closed the dialog without connecting

        settings = dialog.settings
        try:
            window = MainWindow(settings.ip, settings.port, settings.nickname, use_tls=settings.tls)
        except ConnectionError as e:
            QMessageBox.warning(None, 'Connection failed', str(e))
            # Re-open the dialog prefilled with what they just tried.
            nickname, host, port, use_tls = settings.nickname, settings.ip, settings.port, settings.tls
            continue

        app.exec_()
        return
