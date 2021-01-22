import json
import logging
import socket

from PyQt5.QtCore import QThread, pyqtSignal

import constants
import helpers


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
                    raw_length = self.client.recv(constants.HEADER_LENGTH).decode('utf-8')
                    if not raw_length:
                        continue
                    raw = self.client.recv(int(raw_length)).decode('utf-8')
                    if not raw:
                        continue
                    message = json.loads(raw)

                    if message['type'] == constants.Types.REQUEST:
                        self.log(f'Data[{int(raw_length)}] received, {message["type"]}/{message["request"]}.',
                                 level=logging.DEBUG)
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
