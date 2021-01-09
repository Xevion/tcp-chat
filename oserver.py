import json
import random
import socket
import threading
import time
import traceback
import uuid
import logging
from pprint import pprint

import constants
import helpers

# Connection Data
host = '127.0.0.1'
port = 55555
HEADER_LENGTH = 10

# Starting Server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()

logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] [%(name)s] [%(threadName)s] %(message)s')
logger = logging.getLogger('server')

# Lists For Clients and Their Nicknames
clients = {}


def broadcast_data(data):
    for client in clients.values():
        client['client'].send(data)


# Handling Messages From Clients
def handle(client_id):
    logger.info(f'Beginning handling of {client_id}')
    client = clients[client_id]['client']
    nickname = clients[client_id]['nickname']

    while True:
        try:
            # Broadcasting Messages
            length = int(client.recv(HEADER_LENGTH).decode('utf-8'))
            logger.debug(f'Header received - Length {length}')
            message = json.loads(client.recv(length).decode('utf-8'))
            logger.info(f'Data received/parsed, type: {message["type"]}')

            if message['type'] == constants.Types.REQUEST:
                if message['request'] == constants.Requests.REFRESH_CONNECTIONS_LIST:
                    client.send(helpers.prepare_json(
                        {
                            'type': constants.Types.USER_LIST,
                            'users': [
                                {
                                    'nickname': other['nickname'],
                                    'color': other['color']
                                } for other in clients.values()
                            ]
                        }
                    ))
            elif message['type'] == constants.Types.NICKNAME:
                nickname = message['nickname']
                if not clients[client_id]['has_nickname']:
                    logger.info("Nickname is {}".format(nickname))
                    broadcast_data(helpers.prepare_server_message(
                        nickname='Server',
                        message=f'{nickname} joined!',
                        color=constants.Colors.BLACK
                    ))
                    clients[client_id]['has_nickname'] = True
                else:
                    logger.info(f'{clients[client_id]["nickname"]} changed their name to {nickname}')
                clients[client_id]['nickname'] = nickname
            elif message['type'] == constants.Types.MESSAGE:
                broadcast_data(helpers.prepare_server_message(
                    nickname=nickname,
                    message=message['content'],
                    color=clients[client_id]['color']
                ))

                # Basic command processing
                if message['content'] == '/reroll':
                    color = random.choice(constants.Colors.ALL)
                    colorName = constants.Colors.ALL_NAMES[constants.Colors.ALL.index(color)]
                    clients[client_id]['color'] = color
                    broadcast_data(helpers.prepare_server_message(
                        nickname='Server',
                        message=f'Changed your color to {colorName} ({color})',
                        color=constants.Colors.BLACK
                    ))
        except:
            traceback.print_exc()
            logger.info(f'Client {client_id} closed. ({clients[client_id]["nickname"]})')
            client.close()
            del clients[client_id]
            broadcast_data(helpers.prepare_server_message(
                nickname='Server',
                message=f'{nickname} left!',
                color=constants.Colors.BLACK
            ))
            break


# Receiving / Listening Function
def receive():
    while True:
        # Accept Connection
        client, address = server.accept()
        logger.info("New Client from {}".format(str(address)))

        # Request And Store Nickname
        client_id = str(uuid.uuid4())
        client.send(helpers.prepare_json(
            {
                'type': constants.Types.REQUEST,
                'request': constants.Requests.REQUEST_NICK
            }
        ))

        clients[client_id] = {
            'client': client,
            'id': client_id,
            'nickname': client_id[:10],
            'first_seen': int(time.time()),
            'has_nickname': False,
            'color': random.choice(constants.Colors.ALL)
        }
        # pprint(clients[client_id])

        client.send(helpers.prepare_json(
            {
                'type': constants.Types.SERVER_MESSAGE,
                'content': 'Connected to server!'
            }
        ))

        # Start Handling Thread For Client
        thread = threading.Thread(target=handle, args=(client_id,), name=client_id[:8])
        thread.start()


receive()
