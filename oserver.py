import json
import random
import socket
import threading
import time
import traceback
import uuid
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

# Lists For Clients and Their Nicknames
clients = {}


def broadcast_data(data):
    for client in clients.values():
        client['client'].send(data)


# Handling Messages From Clients
def handle(client_id):
    client = clients[client_id]['client']
    nickname = clients[client_id]['nickname']

    while True:
        try:
            # Broadcasting Messages
            length = int(client.recv(HEADER_LENGTH).decode('utf-8'))
            message = json.loads(client.recv(length).decode('utf-8'))

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
                    print("Nickname is {}".format(nickname))
                    broadcast_data(helpers.prepare_json(
                        {
                            'type': constants.Types.MESSAGE,
                            'nickname': 'Server',
                            'content': f'{nickname} joined!',
                            'color': constants.Colors.PINK,
                            'time': int(time.time())
                        }
                    ))
                    clients[client_id]['has_nickname'] = True
                else:
                    print(f'{clients[client_id]["nickname"]} changed their name to {nickname}')
                clients[client_id]['nickname'] = nickname

            elif message['type'] == constants.Types.MESSAGE:
                if message['content'] == '/reroll':
                    color = random.choice(constants.Colors.ALL)
                    colorname = constants.Colors.ALL_NAMES[constants.Colors.ALL.index(color)]
                    clients[client_id]['color'] = color
                    broadcast_data(helpers.prepare_json(
                        {
                            'type': constants.Types.MESSAGE,
                            'nickname': 'Server',
                            'content': f'Changed your color to {colorname} ({color})',
                            'color': constants.Colors.PINK,
                            'time': int(time.time())
                        }
                    ))
                broadcast_data(helpers.prepare_json(
                    {
                        'type': constants.Types.MESSAGE,
                        'nickname': nickname,
                        'content': message["content"],
                        'color': clients[client_id]['color'],
                        'time': int(time.time())
                    }
                ))
        except:
            traceback.print_exc()
            print(f'Closing Client {clients[client_id]["nickname"]}')
            client.close()
            del clients[client_id]
            broadcast_data(helpers.prepare_json(
                {
                    'type': constants.Types.MESSAGE,
                    'nickname': 'Server',
                    'content': f'{nickname} left!',
                    'color': constants.Colors.PINK,
                    'time': int(time.time())
                }
            ))
            break


# Receiving / Listening Function
def receive():
    while True:
        # Accept Connection
        client, address = server.accept()
        print("New Client from {}".format(str(address)))

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
        pprint(clients[client_id])

        client.send(helpers.prepare_json(
            {
                'type': constants.Types.SERVER_MESSAGE,
                'content': 'Connected to server!'
            }
        ))

        # Start Handling Thread For Client
        thread = threading.Thread(target=handle, args=(client_id,))
        thread.start()


receive()
