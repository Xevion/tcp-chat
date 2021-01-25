from typing import Tuple

from PyQt5.QtWidgets import QApplication

from client.dialog import ConnectionDialog
from client.gui import MainWindow


# def connection_dialog() -> Tuple[str, int, str, str, bool]:
#     connect_dialog = ConnectionDialog()


def main():
    app = QApplication([])
    app.setApplicationName("TCPChat Client")
    connect_dialog = ConnectionDialog()
    # m = MainWindow()
    app.exec_()
    if connect_dialog.connect_pressed:
        print(connect_dialog.settings)
