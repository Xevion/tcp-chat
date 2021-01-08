import socket
import threading

from config import config

HEADER_LENGTH = int(config['DEFAULT']['HeaderLength'])

nickname = input("Nickname: ")

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 55555))


def send_message(message):
    header = f'{len(message):<{HEADER_LENGTH}}'
    final = header + message
    client.send(final.encode('ascii'))


def receive():
    while True:
        try:
            length = int(client.recv(HEADER_LENGTH).decode('ascii'))
            message = client.recv(length).decode('ascii')
            if message == 'NICK':
                send_message(nickname)
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
        send_message(message)


# Starting Threads For Listening And Writing
receive_thread = threading.Thread(target=receive)
receive_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()
