import json

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
