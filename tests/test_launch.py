import launch


def test_server_arguments_parse():
    args = launch.build_parser().parse_args(['server', '--host', '0.0.0.0', '--port', '6000', '--tls'])
    assert args.role in ('server', 's', '2')
    assert args.host == '0.0.0.0'
    assert args.port == 6000
    assert args.tls is True


def test_client_alias_and_random_flag():
    args = launch.build_parser().parse_args(['c', '--random'])
    assert args.role in ('client', 'c', '1')
    assert args.random is True


def test_tls_is_none_when_not_passed():
    args = launch.build_parser().parse_args(['server'])
    assert args.tls is None
    assert args.port is None


def test_a_role_is_required():
    import pytest
    with pytest.raises(SystemExit):
        launch.build_parser().parse_args([])
