from shared.config import Config


def test_cli_value_overrides_everything():
    config = Config({'server': {'port': 6000}})
    assert config.get('server', 'port', cli=7000, default=5555) == 7000


def test_file_value_used_when_no_cli():
    config = Config({'server': {'port': 6000}})
    assert config.get('server', 'port', cli=None, default=5555) == 6000


def test_top_level_key_is_a_fallback():
    config = Config({'host': '1.2.3.4'})
    assert config.get('server', 'host', default='127.0.0.1') == '1.2.3.4'


def test_default_when_absent():
    assert Config({}).get('server', 'port', default=5555) == 5555


def test_load_missing_file_is_empty(tmp_path):
    config = Config.load(str(tmp_path / 'nope.toml'))
    assert config.data == {}


def test_load_reads_toml(tmp_path):
    path = tmp_path / 'tcp-chat.toml'
    path.write_text('[server]\nport = 6000\nhost = "0.0.0.0"\n')
    config = Config.load(str(path))
    assert config.get('server', 'port') == 6000
    assert config.get('server', 'host') == '0.0.0.0'
