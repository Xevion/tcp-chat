from shared import helpers
from shared import protocol


def test_prepare_json_round_trips():
    import json
    framed = helpers.prepare_json({'type': 'MESSAGE', 'content': 'hello'})
    header, body = framed[:protocol.HEADER_LENGTH], framed[protocol.HEADER_LENGTH:]
    assert int(header) == len(body)
    assert json.loads(body.decode('utf-8'))['content'] == 'hello'


def test_sizeof_fmt_scales_units():
    assert helpers.sizeof_fmt(0).strip() == '0B'
    assert helpers.sizeof_fmt(1023).strip() == '1023B'
    assert helpers.sizeof_fmt(1024).strip() == '1KiB'
    assert helpers.sizeof_fmt(1024 ** 2).strip() == '1MiB'


def test_formatted_message_escapes_html():
    formatted = helpers.formatted_message({
        'nickname': '<b>nick</b>',
        'message': '<script>',
        'color': '#ff0000',
        'time': 0,
    })
    assert '&lt;b&gt;nick&lt;/b&gt;' in formatted
    assert '<script>' not in formatted
    assert '#ff0000' in formatted


def test_formatted_message_includes_a_timestamp():
    import re
    formatted = helpers.formatted_message({
        'nickname': 'a', 'message': 'hi', 'color': '#fff', 'time': 0,
    })
    assert re.search(r'\[\d{2}:\d{2}\]', formatted) is not None
