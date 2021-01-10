import json
import socket
import traceback

from PyQt5.QtCore import QThread, pyqtSignal, Qt, QEvent, QTimer
from PyQt5.QtWidgets import QMainWindow

import constants
import helpers
from client.MainWindow import Ui_MainWindow
from client.dialog import NicknameDialog

IP = '127.0.0.1'
PORT = 55555

HEADER_LENGTH = 10


class ReceiveWorker(QThread):
    messages = pyqtSignal(str, str, str, int)
    client_list = pyqtSignal(list)
    error = pyqtSignal()
    sent_nick = pyqtSignal()

    def __init__(self, client: socket.socket, nickname: str, parent=None):
        QThread.__init__(self, parent)
        self.client = client
        self.nickname = nickname

    def run(self):
        while True:
            try:
                raw_length = self.client.recv(HEADER_LENGTH).decode('utf-8')
                if not raw_length:
                    continue
                raw = self.client.recv(int(raw_length)).decode('utf-8')
                if not raw:
                    continue
                message = json.loads(raw)

                if message['type'] == constants.Types.REQUEST:
                    if message['request'] == constants.Requests.REQUEST_NICK:
                        self.client.send(helpers.prepare_json(
                            {
                                'type': constants.Types.NICKNAME,
                                'nickname': self.nickname
                            }
                        ))
                        self.sent_nick.emit()
                elif message['type'] == constants.Types.MESSAGE:
                    self.messages.emit(message['nickname'], message['content'], message['color'], message['time'])
                elif message['type'] == constants.Types.USER_LIST:
                    self.client_list.emit(message['users'])
            except:
                traceback.print_exc()
                self.error.emit()
                self.client.close()
                break


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.show()
        self.closed = False

        # Get Nickname
        while True:
            self.nicknameDialog = NicknameDialog(self)
            self.nicknameDialog.exec_()
            self.nickname = self.nicknameDialog.lineEdit.text().strip()
            if len(self.nickname) >= 3 or self.closed:
                break

        # Connect to server
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((IP, PORT))

        # Setup message receiving thread worker
        self.receiveThread = ReceiveWorker(self.client, self.nickname)
        self.receiveThread.messages.connect(self.addMessage)
        self.receiveThread.client_list.connect(self.updateConnectionsList)
        self.receiveThread.start()

        self.connectionsListTimer = QTimer()
        self.connectionsListTimer.timeout.connect(self.refreshConnectionsList)
        self.connectionsListTimer.start(1000 * 30)
        self.receiveThread.sent_nick.connect(self.refreshConnectionsList)

        self.messageBox.setPlaceholderText('Type your message here...')
        self.messageBox.installEventFilter(self)

        self.messages = []

    def closeEvent(self, event):
        if self.nicknameDialog:
            self.closed = True
            self.nicknameDialog.close()
        event.accept()  # let the window close

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and obj is self.messageBox:
            if event.key() == Qt.Key_Return and self.messageBox.hasFocus():
                self.sendMessage(self.messageBox.toPlainText())
                self.messageBox.clear()
                self.messageBox.setText('')
                cursor = self.messageBox.textCursor()
                cursor.setPosition(0)
                self.messageBox.setTextCursor(cursor)
        return super().eventFilter(obj, event)

    def addMessage(self, nickname: str, message: str, color: str, time: int) -> None:
        self.messages.append([nickname, message, color, time])
        self.messageHistory.append(f'&lt;<span style="color: {color}">{nickname}</span>&gt; {message}')

    def sendMessage(self, message: str) -> None:
        message = message.strip()
        if len(message) > 0:
            self.client.send(helpers.prepare_json(
                {
                    'type': constants.Types.MESSAGE,
                    'content': message
                }
            ))

    def refreshConnectionsList(self):
        self.client.send(helpers.prepare_json(
            {
                'type': constants.Types.REQUEST,
                'request': constants.Requests.REFRESH_CONNECTIONS_LIST
            }
        ))

    def updateConnectionsList(self, users):
        self.connectionsList.clear()

        self.connectionsList.addItems([user['nickname'] for user in users])
