import socket

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QDialog, QDialogButtonBox, QVBoxLayout

from config import config
from client.MainWindow import Ui_MainWindow

IP = '127.0.0.1'
PORT = 55555

HEADER_LENGTH = int(config.get(IP, 'HeaderLength'))

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
                message = self.client.recv(length)
                if message == 'NICK':
                    self.client.send(self.nickname.encode('ascii'))
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

        self.receiveThread = ReceiveWorker(self.client, self.nickname)
        self.receiveThread.messages.connect(self.addMessage)
        self.receiveThread.start()
        self.show()

    def addMessage(self, message: str):
        self.textBrowser.append(message)
