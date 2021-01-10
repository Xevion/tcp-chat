import json
import time

import constants

HEADER_LENGTH = 10


def prepare(message: str, encoding='utf-8') -> bytes:
    """Prepares a message for sending through a socket by adding a proper header and encoding it."""
    header = f'{len(message):<{HEADER_LENGTH}}'
    return (header + message).encode(encoding)


def prepare_json(object) -> bytes:
    """
    Prepares a object for sending as encoded JSON with a header.

    :param object: A JSON-encodable object
    :return: Encoded JSON
    """
    return prepare(json.dumps(object))


def prepare_message(nickname: str, message: str, color: str, msgtime: int = None):
    return prepare_json(
        {
            'type': constants.Types.MESSAGE,
            'nickname': nickname,
            'content': message,
            'color': color,
            'time': msgtime or int(time.time())
        }
    )


def prepare_request(request: str) -> bytes:
    """Helper function for creating a request message."""
    return prepare_json({'type': constants.Types.REQUEST, 'request': request})
