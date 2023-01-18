import logging
import socket
import sys
import threading

from server import handler
from shared import constants
from shared import tls

logger = logging.getLogger('server')
logger.setLevel(logging.DEBUG)


def serve(host: str = constants.DEFAULT_IP, port: int = constants.DEFAULT_PORT, use_tls: bool = False) -> None:
    """Bind to host/port and accept clients until interrupted."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(1)
    server.settimeout(0.5)

    tls_context = tls.server_context(constants.TLS_CERT, constants.TLS_KEY) if use_tls else None

    clients = []
    stop_flag: bool = False
    try:
        logger.debug(f'Waiting for connections on {host}:{port}...')
        while True:
            try:
                # Accept Connection
                conn, address = server.accept()
                if tls_context is not None:
                    conn = tls_context.wrap_socket(conn, server_side=True)
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
    serve()
