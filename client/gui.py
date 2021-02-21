import logging
import socket
from typing import List

from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QMainWindow, QLabel
from sortedcontainers import SortedList

import constants
import helpers
from client.ui.MainWindow import Ui_MainWindow
from client.worker import ReceiveWorker

IP = '127.0.0.1'
PORT = 55555

logging.basicConfig(format='[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s')
logger = logging.getLogger('gui')
logger.setLevel(logging.DEBUG)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, ip: str, port: int, nickname: str, *args, **kwargs):
        # Initial UI setup
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.show()

        self.ip, self.port, self.nickname = ip, port, nickname
        self.closed = False

        # Connect to server
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # TODO: Research more socket options, possibly improving client functionality
        self.client.connect((ip, port))

        # Setup message receiving thread worker
        self.receiveThread = ReceiveWorker(self.client, self.nickname)
        self.receiveThread.messages.connect(self.add_message)  # Adding new messages
        self.receiveThread.client_list.connect(self.update_connections)  # Updating the connections list
        self.receiveThread.logs.connect(self.log)  # Receiving logging messages from a thread
        self.receiveThread.data_stats.connect(self.count_stats)  # Receiving data usage stats
        # TODO: Improve initial client/server data exchange
        self.receiveThread.start()

        # Setup message box return key logic
        self.messageBox.installEventFilter(self)

        self.data_stats = QLabel("0.00KB Sent, 0.00KB Received")
        self.data_stats.setAlignment(Qt.AlignVCenter)
        self.status_bar.addPermanentWidget(self.data_stats)

        # Variables for managing
        self.messages = SortedList(key=lambda message: message['time'])
        self.added_messages = []
        self.max_message_id = -1

        self.sent, self.received = 0, 0

    def count_stats(self, sent: bool, change: int) -> None:
        """Handler for counting data statistics."""
        if change != 0:
            if sent:
                self.sent += change
            else:
                self.received += change
            self.data_stats.setText(f'{helpers.sizeof_fmt(self.sent)} Sent, '
                                    f'{helpers.sizeof_fmt(self. received)} Received')

    @staticmethod
    def log(log_data: dict) -> None:
        """Handler for data logging from a thread."""
        logger.log(level=log_data['level'], msg=log_data['message'], exc_info=log_data['error'])

    def closeEvent(self, event):
        """Handle closing by stopping the receive thread."""
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
        scrollbar = self.messageHistory.verticalScrollBar()
        last_position = scrollbar.value()
        at_maximum = last_position == scrollbar.maximum()

        self.messageHistory.setText('<br>'.join(
            msg['compiled'] for msg in self.messages
        ))

        scrollbar.setValue(scrollbar.maximum() if at_maximum else last_position)

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

    def update_connections(self, users: List[dict]):
        """Update the Connections List widget"""
        self.connectionsList.clear()
        self.connectionsList.addItems([user['nickname'] for user in users])
