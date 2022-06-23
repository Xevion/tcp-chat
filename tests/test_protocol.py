import json

import pytest

from shared import protocol


class FakeSocket:
    """A stand-in socket that hands out a byte buffer in fixed-size chunks.

    A chunk size below the frame length forces recv_exact to loop, mimicking the
    partial reads a real TCP stream produces for large messages.
    """

    def __init__(self, data: bytes, chunk_size: int = 1):
        self.data = data
        self.chunk_size = chunk_size
        self.position = 0

    def recv(self, length: int) -> bytes:
        end = min(self.position + min(length, self.chunk_size), len(self.data))
        chunk = self.data[self.position:end]
        self.position = end
        return chunk


def test_encode_uses_byte_length_header():
    framed = protocol.encode({'content': 'hello'})
    header, body = framed[:protocol.HEADER_LENGTH], framed[protocol.HEADER_LENGTH:]
    assert int(header) == len(body)
    assert json.loads(body.decode('utf-8'))['content'] == 'hello'


def test_encode_stamps_protocol_version():
    source = {'content': 'hello'}
    decoded = protocol.read_message(FakeSocket(protocol.encode(source)))
    assert decoded['v'] == protocol.PROTOCOL_VERSION
    # The caller's dict must not be mutated by the stamping.
    assert 'v' not in source


def test_encode_keeps_an_explicit_version():
    framed = protocol.encode({'content': 'hello', 'v': 99})
    assert protocol.read_message(FakeSocket(framed))['v'] == 99


def test_recv_exact_reassembles_fragmented_reads():
    sock = FakeSocket(b'abcdefghij', chunk_size=3)
    assert protocol.recv_exact(sock, 10) == b'abcdefghij'


def test_recv_exact_raises_when_peer_closes_early():
    sock = FakeSocket(b'abc', chunk_size=1)
    with pytest.raises(ConnectionError):
        protocol.recv_exact(sock, 10)


def test_read_message_round_trips_through_a_chunked_socket():
    payload = {'type': 'MESSAGE', 'content': 'a longer message ' * 50}
    sock = FakeSocket(protocol.encode(payload), chunk_size=7)
    decoded = protocol.read_message(sock)
    assert decoded['type'] == payload['type']
    assert decoded['content'] == payload['content']
