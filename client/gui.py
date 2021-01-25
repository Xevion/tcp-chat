import logging
import socket
from pprint import pprint

from PyQt5.QtCore import Qt, QEvent, QTimer
from PyQt5.QtWidgets import QMainWindow

from sortedcontainers import SortedList

import constants
import helpers
from client.MainWindow import Ui_MainWindow
from client.dialog import NicknameDialog
from client.worker import ReceiveWorker

IP = '127.0.0.1'
PORT = 55555

logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s')
logger = logging.getLogger('gui')


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
        self.receiveThread.messages.connect(self.add_message)
        self.receiveThread.client_list.connect(self.update_connections)
        self.receiveThread.logs.connect(self.log)
        self.receiveThread.data_stats.connect(self.count_stats)
        self.receiveThread.sent_nick.connect(self._ready)
        self.receiveThread.start()

        # Setup
        self.connectionsListTimer = QTimer()
        self.connectionsListTimer.timeout.connect(self.refresh_connections)
        self.connectionsListTimer.start(1000 * 30)

        self.messageBox.setPlaceholderText('Type your message here...')
        self.messageBox.installEventFilter(self)

        self.messages = SortedList(key=lambda message: message['time'])
        self.added_messages = []
        self.max_message_id = -1

        self.sent, self.received = 0, 0

    def count_stats(self, sent: bool, change: int) -> None:
        if sent:
            self.sent += change
        else:
            self.received += change
        self.data_stats.setText(f'{helpers.sizeof_fmt(self.sent)} Sent, {helpers.sizeof_fmt(self.received)} Received')

    def log(self, log_data: dict) -> None:
        logger.log(level=log_data['level'], msg=log_data['message'], exc_info=log_data['error'])

    def _ready(self):
        logger.debug('Nickname sent. Ready to communicate with server further...')
        self.refresh_connections()
        self.get_message_history()

    def closeEvent(self, event):
        self.receiveThread.stop()
        event.accept()  # let the window close

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.KeyPress and obj is self.messageBox:
            if event.key() == Qt.Key_Return and self.messageBox.hasFocus():
                self.send_message(self.messageBox.toPlainText())
                self.messageBox.clear()
                self.messageBox.setText('')
                cursor = self.messageBox.textCursor()
                cursor.setPosition(0)
                self.messageBox.setTextCursor(cursor)
                return True
        return super().eventFilter(obj, event)

    def refresh_messages(self) -> None:
        """Completely refresh the chat box text."""
        min_time = min(map(lambda msg: msg['time'], self.messages))

        scrollbar = self.messageHistory.verticalScrollBar()
        lastPosition = scrollbar.value()
        atMaximum = lastPosition == scrollbar.maximum()

        self.messageHistory.setText('<br>'.join(
            msg['compiled'] for msg in self.messages
        ))

        scrollbar.setValue(scrollbar.maximum() if atMaximum else lastPosition)

    def send(self, data: bytes, **kwargs) -> None:
        self.count_stats(True, len(data))
        self.client.send(data, **kwargs)

    def add_message(self, message: dict) -> None:
        message_id = message['id']
        if message_id not in self.added_messages:
            message['compiled'] = helpers.formatted_message(message)

            if 0 <= message_id < self.max_message_id:
                logger.info('Refreshing entire chatbox...')
                self.max_message_id = message_id
                self.messages.add(message)
                return
            else:
                self.max_message_id = message_id
                self.added_messages.append(message_id)
                self.messages.add(message)

            self.refresh_messages()

    def send_message(self, message: str) -> None:
        message = message.strip()
        if len(message) > 0:
            self.send(helpers.prepare_json(
                {
                    'type': constants.Types.MESSAGE,
                    'content': message
                }
            ))

    def refresh_connections(self) -> None:
        logger.info('Requesting connections list')
        self.send(helpers.prepare_json(
            {
                'type': constants.Types.REQUEST,
                'request': constants.Requests.REFRESH_CONNECTIONS_LIST
            }
        ))

    def get_message_history(self) -> None:
        logger.info('Requesting message history')
        self.send(helpers.prepare_json(
            {
                'type': constants.Types.REQUEST,
                'request': constants.Requests.GET_MESSAGE_HISTORY
            }
        ))

    def update_connections(self, users):
        self.connectionsList.clear()
        self.connectionsList.addItems([user['nickname'] for user in users])
