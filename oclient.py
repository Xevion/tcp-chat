import socket
import threading

import helpers
from config import config

HEADER_LENGTH = int(config['DEFAULT']['HeaderLength'])

nickname = input("Nickname: ")

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 55555))


def receive():
    while True:
        try:
            length = int(client.recv(HEADER_LENGTH).decode('ascii'))
            message = client.recv(length).decode('ascii')
            if message == 'NICK':
                client.send(helpers.prepare(nickname))
            else:
                print(message)
        except:
            print("Error! Disconnecting.")
            client.close()
            break


# Sending Messages To Server
def write():
    while True:
        message = '{}: {}'.format(nickname, input(''))
        client.send(helpers.prepare(message))


# Starting Threads For Listening And Writing
receive_thread = threading.Thread(target=receive)
receive_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()
