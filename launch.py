#!/usr/bin/env python3
import argparse
import logging

from shared import constants
from shared import logging_config
from shared.config import Config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='tcp-chat', description='A small TCP chat server and client.'
    )
    parser.add_argument(
        '--config', default=None, help='Path to a TOML config file (default: tcp-chat.toml)'
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Log at DEBUG instead of INFO')
    parser.add_argument('--log-file', default=None, help='Also write logs to this file')
    sub = parser.add_subparsers(dest='role')
    sub.required = True

    server = sub.add_parser('server', aliases=['s', '2'], help='Run the chat server')
    server.add_argument('--host', default=None)
    server.add_argument('--port', type=int, default=None)
    server.add_argument('--tls', action='store_true', default=None, help='Serve over TLS')

    client = sub.add_parser('client', aliases=['c', '1'], help='Run the chat client')
    client.add_argument('--host', default=None)
    client.add_argument('--port', type=int, default=None)
    client.add_argument('--nickname', default=None)
    client.add_argument('--random', action='store_true', help='Use a random nickname')
    client.add_argument('--tls', action='store_true', default=None, help='Connect over TLS')

    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    logging_config.configure(
        level=logging.DEBUG if args.verbose else logging.INFO, logfile=args.log_file
    )
    config = Config.load(args.config) if args.config else Config.load()

    if args.role in ('server', 's', '2'):
        host = config.get('server', 'host', cli=args.host, default=constants.DEFAULT_IP)
        port = config.get('server', 'port', cli=args.port, default=constants.DEFAULT_PORT)
        use_tls = config.get('server', 'tls', cli=args.tls, default=constants.USE_TLS)
        from server.main import serve

        serve(host, port, use_tls)
    else:
        nickname = args.nickname
        if args.random:
            from faker import Faker

            nickname = Faker().user_name()
        nickname = config.get('client', 'nickname', cli=nickname, default=None)
        host = config.get('client', 'host', cli=args.host, default=constants.DEFAULT_IP)
        port = config.get('client', 'port', cli=args.port, default=constants.DEFAULT_PORT)
        use_tls = config.get('client', 'tls', cli=args.tls, default=constants.USE_TLS)
        from client.main import main as client_main

        client_main(nickname, host=host, port=port, use_tls=use_tls)


if __name__ == '__main__':
    main()
