import html
import json
import time
from typing import List, Tuple, Any

from shared import constants

HEADER_LENGTH = 10


def prepare(message: str, encoding='utf-8') -> bytes:
    """Prepares a message for sending through a socket by adding a proper header and encoding it."""
    header = f'{len(message):<{HEADER_LENGTH}}'
    return (header + message).encode(encoding)


def prepare_json(obj: Any) -> bytes:
    """
    Prepares a object for sending as encoded JSON with a header.

    :param obj: A JSON-encodable object
    :return: Encoded JSON
    """
    return prepare(json.dumps(obj))


def prepare_message(nickname: str, message: str, color: str, message_id: int, timestamp: int = None) -> bytes:
    return prepare_json(
        {
            'type': constants.Types.MESSAGE,
            'nickname': nickname,
            'content': message,
            'color': color,
            'time': timestamp or int(time.time()),
            'id': message_id,
        }
    )


def prepare_message_history(messages: List[Tuple[int, str, str, str, int]]) -> bytes:
    """Returns a encoded JSON message history object with the messages provided"""
    return prepare_json(
        {
            'type': constants.Types.MESSAGE_HISTORY,
            'messages': [
                {
                    'type': constants.Types.MESSAGE,
                    'nickname': nickname,
                    'content': message,
                    'color': color,
                    'time': timestamp,
                    'id': message_id
                } for message_id, nickname, color, message, timestamp in messages
            ]
        }
    )


def prepare_request(request: str) -> bytes:
    """Helper function for creating a request message."""
    return prepare_json({'type': constants.Types.REQUEST, 'request': request})


def formatted_message(message: dict) -> str:
    """Given a message dict object, return a color formatted and GUI ready string."""
    nick_esc = html.escape(message["nickname"])
    msg_esc = html.escape(message["message"])
    return f'&lt;<span style="color: {message["color"]}">{nick_esc}</span>&gt; {msg_esc}'


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.0f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
