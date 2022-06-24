import json
import logging
import socket

from PyQt5.QtCore import QThread, pyqtSignal

from shared import constants
from shared import helpers
from shared import protocol


class ReceiveWorker(QThread):
    messages = pyqtSignal(dict)
    client_list = pyqtSignal(list)
    error = pyqtSignal()
    sent_nick = pyqtSignal()
    logs = pyqtSignal(dict)
    data_stats = pyqtSignal(bool, int)  # bool: True if sent stats change, False if received stats change

    def __init__(self, client: socket.socket, nickname: str, parent=None):
        QThread.__init__(self, parent)
        self.client = client
        self.nickname = nickname
        self.__isRunning = True

    def stop(self) -> None:
        self.__isRunning = False

    @staticmethod
    def __extract_message(data) -> dict:
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

    def send(self, data: bytes, **kwargs) -> None:
        self.data_stats.emit(True, len(data))
        self.client.send(data, **kwargs)

    def run(self):
        try:
            while self.__isRunning:
                try:
                    # Receive the header, then exactly the body length it describes
                    raw_header = protocol.recv_exact(self.client, protocol.HEADER_LENGTH)
                    length = int(raw_header.decode('utf-8'))

                    raw_data = protocol.recv_exact(self.client, length)
                    message = json.loads(raw_data.decode('utf-8'))

                    self.data_stats.emit(False, len(raw_header) + len(raw_data))

                    if message['type'] == constants.Types.REQUEST:
                        self.log(f'Data[{length}] received, {message["type"]}/{message["request"]}.',
                                 level=logging.DEBUG)
                    else:
                        self.log(f'Data[{length}] received, {message["type"]}.', level=logging.DEBUG)

                    if message['type'] == constants.Types.REQUEST:
                        if message['request'] == constants.Requests.REQUEST_NICK:
                            self.send(helpers.prepare_json(
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
