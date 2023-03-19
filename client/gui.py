import logging
import socket
from typing import List

from PyQt5.QtCore import Qt, QEvent, QTimer
from PyQt5.QtWidgets import QMainWindow, QLabel
from sortedcontainers import SortedList

from shared import constants
from shared import helpers
from shared import tls
from shared.backoff import backoff_delays
from client.ui.MainWindow import Ui_MainWindow
from client.worker import ReceiveWorker

logging.basicConfig(format='[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s')
logger = logging.getLogger('gui')
logger.setLevel(logging.DEBUG)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, ip: str, port: int, nickname: str, use_tls: bool = False, *args, **kwargs):
        # Initial UI setup
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.show()

        self.ip, self.port, self.nickname = ip, port, nickname
        self.use_tls = use_tls
        self.closed = False
        self._reconnect_delays = None
        self._stability_timer = None

        # Connect to server
        if not self.open_socket():
            raise ConnectionError(f'Could not connect to {ip}:{port}')

        # Setup message receiving thread worker
        self.start_worker()

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

    def open_socket(self) -> bool:
        """Open a fresh connection to the server, wrapping it in TLS when enabled."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.use_tls:
                context = tls.client_context(verify=constants.TLS_VERIFY)
                sock = context.wrap_socket(sock, server_hostname=self.ip)
            sock.connect((self.ip, self.port))
            self.client = sock
            return True
        except OSError:
            return False

    def start_worker(self) -> None:
        """Spin up a receive worker bound to the current socket and wire its signals."""
        self.receiveThread = ReceiveWorker(self.client, self.nickname)
        self.receiveThread.messages.connect(self.add_message)  # Adding new messages
        self.receiveThread.client_list.connect(self.update_connections)  # Updating the connections list
        self.receiveThread.logs.connect(self.log)  # Receiving logging messages from a thread
        self.receiveThread.data_stats.connect(self.count_stats)  # Receiving data usage stats
        self.receiveThread.error.connect(self.on_connection_lost)  # Reconnect when the socket drops
        self.receiveThread.start()
        # Treat the link as healthy once it survives a few seconds, resetting the
        # backoff so a later, unrelated drop starts its own fresh sequence.
        self._arm_stability_timer()

    def on_connection_lost(self) -> None:
        """Schedule a backoff-driven reconnect after the worker reports a dropped socket."""
        if self.closed:
            return
        self._cancel_stability_timer()
        # Keep advancing the existing backoff; resetting it on every drop turns a
        # connection that flaps immediately into a tight reconnect loop.
        if self._reconnect_delays is None:
            self._reconnect_delays = backoff_delays()
        delay = next(self._reconnect_delays)
        self.status_bar.showMessage(f'Connection lost, reconnecting in {delay:.0f}s...')
        QTimer.singleShot(int(delay * 1000), self.try_reconnect)

    def try_reconnect(self) -> None:
        """Attempt a single reconnect, rescheduling itself with backoff on failure."""
        if self.closed:
            return
        if self.open_socket():
            self.status_bar.showMessage('Reconnected.', 3000)
            self.start_worker()
        else:
            delay = next(self._reconnect_delays)
            QTimer.singleShot(int(delay * 1000), self.try_reconnect)

    def _arm_stability_timer(self) -> None:
        self._cancel_stability_timer()
        self._stability_timer = QTimer(self)
        self._stability_timer.setSingleShot(True)
        self._stability_timer.timeout.connect(self._mark_connection_stable)
        self._stability_timer.start(5000)

    def _cancel_stability_timer(self) -> None:
        if self._stability_timer is not None:
            self._stability_timer.stop()
            self._stability_timer = None

    def _mark_connection_stable(self) -> None:
        self._reconnect_delays = None

    def count_stats(self, sent: bool, change: int) -> None:
        """Handler for counting data statistics."""
        if change != 0:
            if sent:
                self.sent += change
            else:
                self.received += change
            self.data_stats.setText(f'{helpers.sizeof_fmt(self.sent)} Sent, '
                                    f'{helpers.sizeof_fmt(self.received)} Received')

    @staticmethod
    def log(log_data: dict) -> None:
        """Handler for data logging from a thread."""
        logger.log(level=log_data['level'], msg=log_data['message'], exc_info=log_data['error'])

    def closeEvent(self, event):
        """Handle closing by telling the server goodbye and stopping the receive thread."""
        self.closed = True  # stop any reconnect attempts from rescheduling
        try:
            self.send(helpers.prepare_quit())
        except OSError:
            pass  # socket already gone; nothing to announce
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
                msg['compiled'] for msg in helpers.tail(self.messages, constants.MAX_SCROLLBACK)
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
