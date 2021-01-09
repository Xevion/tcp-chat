import json
import socket
import threading
import time
import traceback
import uuid

import constants
import helpers
from config import config

# Connection Data
host = '127.0.0.1'
port = 55555
HEADER_LENGTH = int(config['DEFAULT']['HeaderLength'])

# Starting Server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()

# Lists For Clients and Their Nicknames
clients = {}


# Sending Messages To All Connected Clients
def broadcast(message):
    print(f'"{message}"')
    encoded = helpers.prepare_json({
        'type': constants.Types.MESSAGE,
        'content': message
    })
    for client in clients.values():
        client['client'].send(encoded)


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
                                clients[other]['nickname'] for other in clients.keys() if other != client_id
                            ]
                        }
                    ))
            elif message['type'] == constants.Types.NICKNAME:

                nickname = message['nickname']
                if not clients[client_id]['has_nickname']:
                    print("Nickname is {}".format(nickname))
                    broadcast("{} joined!".format(nickname))
                    clients[client_id]['has_nickname'] = True
                else:
                    print(f'{clients[client_id]["nickname"]} changed their name to {nickname}')
                clients[client_id]['nickname'] = nickname

            elif message['type'] == constants.Types.MESSAGE:
                broadcast(f'<{nickname}>: {message["content"]}')

        except:
            # Removing And Closing Clients
            client.close()
            del clients[client_id]
            broadcast('{} left!'.format(nickname))
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
            'nickname': client_id[:10],
            'first_seen': int(time.time()),
            'has_nickname': False
        }

        client.send(helpers.prepare_json(
            {
                'type': constants.Types.MESSAGE,
                'content': 'Connected to server!'
            }
        ))

        # Start Handling Thread For Client
        thread = threading.Thread(target=handle, args=(client_id,))
        thread.start()


receive()
