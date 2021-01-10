import logging
import socket
import threading

from server import handler

host = '127.0.0.1'
port = 55555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()

logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s')
logger = logging.getLogger('server')

clients = []

# Receiving / Listening Function
def receive():
    while True:
        # Accept Connection
        conn, address = server.accept()
        logger.info(f"New connection from {address}")

        client = handler.Client(conn, address, clients)
        client.request_nickname()

        # Start Handling Thread For Client
        thread = threading.Thread(target=client.handle, name=client.id[:8])
        thread.start()
