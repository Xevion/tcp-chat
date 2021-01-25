import logging
import socket
import threading

import constants
from server import handler

host = constants.DEFAULT_IP
port = constants.DEFAULT_PORT

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()

logger = logging.getLogger('server')
logger.setLevel(logging.DEBUG)

clients = []


# Receiving / Listening Function
def receive():
    while True:
        try:
            # Accept Connection
            conn, address = server.accept()
            logger.info(f"New connection from {address}")

            client = handler.Client(conn, address, clients)
            clients.append(client)
            client.request_nickname()

            # Inform all clients of new client, give new client connections list
            for client in clients:
                client.send_connections_list()

            # Start Handling Thread For Client
            thread = threading.Thread(target=client.handle, name=client.id[:8])
            thread.start()
        except KeyboardInterrupt:
            logger.info('Server closed by user.')
        except Exception as e:
            logger.critical(e, exc_info=e)


if __name__ == '__main__':
    receive()
