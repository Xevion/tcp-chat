from shared import helpers


def test_prepare_prefixes_a_fixed_width_header():
    framed = helpers.prepare('hi')
    # 10-byte left-justified length header, then the body.
    assert framed == b'2         hi'
    assert len(framed) == helpers.HEADER_LENGTH + 2


def test_prepare_json_round_trips():
    import json
    framed = helpers.prepare_json({'type': 'MESSAGE', 'content': 'hello'})
    header, body = framed[:helpers.HEADER_LENGTH], framed[helpers.HEADER_LENGTH:]
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
    })
    assert '&lt;b&gt;nick&lt;/b&gt;' in formatted
    assert '<script>' not in formatted
    assert '#ff0000' in formatted
