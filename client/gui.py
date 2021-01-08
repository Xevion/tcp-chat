import socket
from pprint import pprint

from PyQt5.QtCore import QThread, pyqtSignal, Qt, QEvent
from PyQt5.QtWidgets import QMainWindow, QDialog, QDialogButtonBox, QVBoxLayout

from client.MainWindow import Ui_MainWindow
from config import config

IP = '127.0.0.1'
PORT = 55555

HEADER_LENGTH = 10


class ReceiveWorker(QThread):
    messages = pyqtSignal(str)
    error = pyqtSignal()

    def __init__(self, client: socket.socket, nickname: str, parent=None):
        QThread.__init__(self, parent)
        self.client = client
        self.nickname = nickname

    def run(self):
        while True:
            try:
                length = int(self.client.recv(HEADER_LENGTH).decode('ascii'))
                message = self.client.recv(length).decode('ascii')
                if message == 'NICK':
                    header = f'{len(self.nickname):<{HEADER_LENGTH}}'
                    final = header + self.nickname
                    pprint(final)
                    self.client.send(final.encode('ascii'))
                else:
                    self.messages.emit(message)
            except:
                self.error.emit()
                self.client.close()
                break


class CustomDialog(QDialog):

    def __init__(self, *args, **kwargs):
        super(CustomDialog, self).__init__(*args, **kwargs)

        self.setWindowTitle("HELLO!")

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((IP, PORT))

        # nicknameDialog = CustomDialog(self)
        # if nicknameDialog.exec_():
        #     print('s')

        self.nickname = 'Default'

        self.textEdit.installEventFilter(self)

        self.receiveThread = ReceiveWorker(self.client, self.nickname)
        self.receiveThread.messages.connect(self.addMessage)
        self.receiveThread.start()

        self.show()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and obj is self.textEdit:
            if event.key() == Qt.Key_Return and self.textEdit.hasFocus():
                self.sendMessage(self.textEdit.toPlainText())
                self.textEdit.clear()
        return super().eventFilter(obj, event)

    def addMessage(self, message: str) -> None:
        self.textBrowser.append(message)

    def sendMessage(self, message: str) -> None:
        header = f'{len(message):<{HEADER_LENGTH}}'
        final = header + message
        pprint(final)
        self.client.send(final.encode('ascii'))
