HEADER_LENGTH = 10


def prepare(message: str, encoding='ascii') -> bytes:
    """Prepares a message for sending through a socket by adding a proper header and encoding it."""
    header = f'{len(message):<{HEADER_LENGTH}}'
    return (header + message).encode(encoding)
