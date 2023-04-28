import logging
from typing import List

from PyQt5.QtCore import Qt, QEvent, QTimer
from PyQt5.QtWidgets import QMainWindow, QLabel
from sortedcontainers import SortedList

from shared import constants
from shared import helpers
from client import core
from client.ui.MainWindow import Ui_MainWindow
from client.worker import ReceiveWorker

logger = logging.getLogger('gui')


class MainWindow(QMainWindow, Ui_MainWindow):
    """Thin Qt view over a :class:`client.core.ClientCore`.

    The window holds no socket or protocol logic of its own; it connects through
    the core, renders the events the core's receive loop emits, and drives the
    core's reconnect backoff with a timer. A failed initial connection is raised
    to the caller so it can re-prompt rather than the window crashing mid-build.
    """

    def __init__(self, ip: str, port: int, nickname: str, use_tls: bool = False, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.core = core.ClientCore(ip, port, nickname, use_tls=use_tls)
        self.closed = False
        self._stability_timer = None

        # Connect before showing: a failed connection should come back to the
        # caller as an error, not flash a half-built window on screen.
        result = self.core.connect()
        if not result.ok:
            raise ConnectionError(result.reason or f'Could not connect to {ip}:{port}')

        self.show()

        # Setup message box return key logic
        self.messageBox.installEventFilter(self)

        self.data_stats = QLabel("0.00KB Sent, 0.00KB Received")
        self.data_stats.setAlignment(Qt.AlignVCenter)
        self.status_bar.addPermanentWidget(self.data_stats)

        # Variables for managing messages
        self.messages = SortedList(key=lambda message: message['time'])
        self.added_messages = []
        self.max_message_id = -1

        self.start_worker()

    def start_worker(self) -> None:
        """Spin up a receive worker bound to the core and wire its event signal."""
        self.receiveThread = ReceiveWorker(self.core)
        self.receiveThread.event.connect(self.on_event)
        self.receiveThread.start()
        # Treat the link as healthy once it survives a few seconds, resetting the
        # backoff so a later, unrelated drop starts its own fresh sequence.
        self._arm_stability_timer()

    def on_event(self, event: core.Event) -> None:
        """Render one core event onto the UI."""
        if event.type == core.MESSAGE:
            self.add_message(event.payload)
        elif event.type == core.USER_LIST:
            self.update_connections(event.payload['users'])
        elif event.type == core.STATS:
            self._render_stats()
        elif event.type == core.DISCONNECTED:
            self.on_connection_lost()

    def on_connection_lost(self) -> None:
        """Schedule a backoff-driven reconnect after the core reports a dropped socket."""
        if self.closed:
            return
        self._cancel_stability_timer()
        delay = self.core.next_reconnect_delay()
        self.status_bar.showMessage(f'Connection lost, reconnecting in {delay:.0f}s...')
        QTimer.singleShot(int(delay * 1000), self.try_reconnect)

    def try_reconnect(self) -> None:
        """Attempt a single reconnect, rescheduling itself with backoff on failure."""
        if self.closed:
            return
        result = self.core.connect()
        if result.ok:
            self.status_bar.showMessage('Reconnected.', 3000)
            self.start_worker()
        elif result.permanent:
            # The server stated why it refused us; reconnecting can't fix that.
            self.status_bar.showMessage(f'Cannot reconnect: {result.reason}')
        else:
            delay = self.core.next_reconnect_delay()
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
        self.core.reset_backoff()

    def _render_stats(self) -> None:
        self.data_stats.setText(f'{helpers.sizeof_fmt(self.core.sent)} Sent, '
                                f'{helpers.sizeof_fmt(self.core.received)} Received')

    def closeEvent(self, event):
        """Handle closing by telling the server goodbye and stopping the receive thread."""
        self.closed = True  # stop any reconnect attempts from rescheduling
        self.core.send_quit()
        self.receiveThread.stop()
        self.core.close()  # unblocks the worker's recv so the thread can exit
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
        self.core.send_message(message)
        self._render_stats()

    def update_connections(self, users: List[dict]):
        """Update the Connections List widget"""
        self.connectionsList.clear()
        self.connectionsList.addItems([user['nickname'] for user in users])
