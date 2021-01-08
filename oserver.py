import socket
import threading

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
clients = []
nicknames = []


# Sending Messages To All Connected Clients
def broadcast(message):
    header = f'{len(message):<{HEADER_LENGTH}}'
    final = header + message
    for client in clients:
        client.send(final.encode('ascii'))


def send_message(client, message):
    header = f'{len(message):<{HEADER_LENGTH}}'
    final = header + message
    client.send(final.encode('ascii'))


# Handling Messages From Clients
def handle(client):
    while True:
        try:
            # Broadcasting Messages
            length = int(client.recv(HEADER_LENGTH).decode('ascii'))
            message = client.recv(length).decode('ascii')
            broadcast(message)
        except:
            # Removing And Closing Clients
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]
            broadcast('{} left!'.format(nickname))
            nicknames.remove(nickname)
            break


# Receiving / Listening Function
def receive():
    while True:
        # Accept Connection
        client, address = server.accept()
        print("Connected with {}".format(str(address)))

        # Request And Store Nickname
        send_message(client, 'NICK')
        length = int(client.recv(HEADER_LENGTH).decode('ascii'))
        nickname = client.recv(length).decode('ascii')
        nicknames.append(nickname)
        clients.append(client)

        # Print And Broadcast Nickname
        print("Nickname is {}".format(nickname))
        broadcast("{} joined!".format(nickname))

        send_message(client, 'Connected to server!')

        # Start Handling Thread For Client
        thread = threading.Thread(target=handle, args=(client,))
        thread.start()


receive()
