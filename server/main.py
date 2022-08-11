import logging
import socket
import sys
import threading

from server import handler
from shared import constants

host = constants.DEFAULT_IP
port = constants.DEFAULT_PORT

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen(1)
server.settimeout(0.5)

logger = logging.getLogger('server')
logger.setLevel(logging.DEBUG)

clients = []


# Receiving / Listening Function
def receive():
    stop_flag: bool = False
    try:
        logger.debug('Waiting for connections...')
        while True:
            try:
                # Accept Connection
                conn, address = server.accept()
                logger.info(f"New connection from {address}")

                client = handler.Client(conn, address, clients, lambda: stop_flag)
                clients.append(client)
                client.request_nickname()

                # Inform the new client's room of the arrival
                logger.debug('Informing the room of the incoming connection.')
                client.notify_room(client.room)

                # Start Handling Thread For Client
                thread = threading.Thread(target=client.handle, name=client.id[:8])
                thread.start()
            except socket.timeout:
                pass
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                logger.critical(e, exc_info=e)
                break
    except KeyboardInterrupt:
        logger.info('User stopped server manually. Enabling stop flag.')
        stop_flag = True
        sys.exit()


if __name__ == '__main__':
    receive()
