import logging
import multiprocessing
import socket

from server import handler

host = '127.0.0.1'
port = 55555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()

logger = logging.getLogger('server')

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

            # Start Handling Thread For Client
            thread = multiprocessing.Process(target=client.handle, name=client.id[:8])
            thread.start()
        except KeyboardInterrupt:
            logger.info('Server closed by user.')
        except Exception as e:
            logger.critical(e, exc_info=e)


if __name__ == '__main__':
    from server import db

    receive()
    db.conn.close()
