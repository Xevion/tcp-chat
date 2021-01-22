import json
import logging
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

logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s')
logger = logging.getLogger('gui')

HEADER_LENGTH = 10


class ReceiveWorker(QThread):
    messages = pyqtSignal(dict)
    client_list = pyqtSignal(list)
    error = pyqtSignal()
    sent_nick = pyqtSignal()
    logs = pyqtSignal(dict)

    def __init__(self, client: socket.socket, nickname: str, parent=None):
        QThread.__init__(self, parent)
        self.client = client
        self.nickname = nickname
        self.__isRunning = True

    def stop(self) -> None:
        self.__isRunning = False

    def __extract_message(self, data) -> dict:
        return {
            'nickname': data['nickname'],
            'message': data['content'],
            'color': data['color'],
            'time': data['time'],
            'id': data['id']
        }

    def log(self, message: str, level: int = logging.INFO, error: Exception = None):
        """Send a log message out from this QThread to the MainThread"""
        self.logs.emit(
            {
                'message': message,
                'level': level,
                'error': error
            }
        )

    def run(self):
        try:
            while self.__isRunning:
                try:
                    raw_length = self.client.recv(HEADER_LENGTH).decode('utf-8')
                    if not raw_length:
                        continue
                    raw = self.client.recv(int(raw_length)).decode('utf-8')
                    if not raw:
                        continue
                    message = json.loads(raw)

                    if message['type'] == constants.Types.REQUEST:
                        self.log(f'Data[{int(raw_length)}] received, {message["type"]}/{message["request"]}.', level=logging.DEBUG)
                    else:
                        self.log(f'Data[{int(raw_length)}] received, {message["type"]}.', level=logging.DEBUG)


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
                        self.messages.emit(self.__extract_message(message))
                    elif message['type'] == constants.Types.USER_LIST:
                        self.client_list.emit(message['users'])
                    elif message['type'] == constants.Types.MESSAGE_HISTORY:
                        for submessage in message['messages']:
                            self.messages.emit(self.__extract_message(submessage))

                except Exception as e:
                    self.log(str(e), level=logging.CRITICAL, error=e)
                    self.error.emit()
                    break
        finally:
            self.log('Closing socket.', level=logging.INFO)
            self.client.close()


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
            if len(self.nickname) >= 3:
                self.closed = True
                break
            elif self.closed:
                break

        # Connect to server
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((IP, PORT))

        # Setup message receiving thread worker
        self.receiveThread = ReceiveWorker(self.client, self.nickname)
        self.receiveThread.messages.connect(self.addMessage)
        self.receiveThread.client_list.connect(self.update_connections)
        self.receiveThread.logs.connect(self.log)
        self.receiveThread.start()

        self.connectionsListTimer = QTimer()
        self.connectionsListTimer.timeout.connect(self.refresh_connections)
        self.connectionsListTimer.start(1000 * 30)
        self.receiveThread.sent_nick.connect(self._ready)

        self.messageBox.setPlaceholderText('Type your message here...')
        self.messageBox.installEventFilter(self)

        self.messages = []

    def log(self, log_data: dict) -> None:
        logger.log(level=log_data['level'], msg=log_data['message'], exc_info=log_data['error'])

    def _ready(self):
        logger.debug('Nickname sent. Ready to communicate with server further...')
        self.refresh_connections()
        self.get_message_history()

    def closeEvent(self, event):
        if self.nicknameDialog and not self.closed:
            logger.debug('Closing nickname dialog before main window')
            self.closed = True
            self.nicknameDialog.close()
        else:
            self.receiveThread.stop()
            self.connectionsListTimer.stop()

        event.accept()  # let the window close

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.KeyPress and obj is self.messageBox:
            if event.key() == Qt.Key_Return and self.messageBox.hasFocus():
                self.sendMessage(self.messageBox.toPlainText())
                self.messageBox.clear()
                self.messageBox.setText('')
                cursor = self.messageBox.textCursor()
                cursor.setPosition(0)
                self.messageBox.setTextCursor(cursor)
                return True
        return super().eventFilter(obj, event)

    def addMessage(self, message: dict) -> None:
        self.messages.append(message)
        self.messageHistory.append(
            f'&lt;<span style="color: {message["color"]}">{message["nickname"]}</span>&gt; {message["message"]}')

    def sendMessage(self, message: str) -> None:
        message = message.strip()
        if len(message) > 0:
            logger.info(f'Sending message of length {len(message)}')
            self.client.send(helpers.prepare_json(
                {
                    'type': constants.Types.MESSAGE,
                    'content': message
                }
            ))

    def refresh_connections(self) -> None:
        logger.info('Requesting connections list')
        self.client.send(helpers.prepare_json(
            {
                'type': constants.Types.REQUEST,
                'request': constants.Requests.REFRESH_CONNECTIONS_LIST
            }
        ))

    def get_message_history(self) -> None:
        logger.info('Requesting message history')
        self.client.send(helpers.prepare_json(
            {
                'type': constants.Types.REQUEST,
                'request': constants.Requests.GET_MESSAGE_HISTORY
            }
        ))

    def update_connections(self, users):
        self.connectionsList.clear()
        self.connectionsList.addItems([user['nickname'] for user in users])
