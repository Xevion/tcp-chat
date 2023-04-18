import logging
import socket
import sys
import threading

from server import handler
from shared import constants
from shared import handshake
from shared import protocol

logger = logging.getLogger('server')


def serve(host: str = constants.DEFAULT_IP, port: int = constants.DEFAULT_PORT, use_tls: bool = False) -> None:
    """Bind to host/port and accept clients until interrupted."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # restart without waiting on TIME_WAIT
    server.bind((host, port))
    server.listen(1)
    server.settimeout(0.5)

    clients = []
    stop_flag: bool = False
    try:
        logger.info(f'Waiting for connections on {host}:{port}...')
        while True:
            try:
                conn, address = server.accept()
            except socket.timeout:
                continue

            # A single client's setup failing (e.g. a TLS/plaintext mismatch) must not
            # take down the whole server, so isolate it from the accept loop.
            client = None
            try:
                logger.info(f"New connection from {address}")

                # Negotiate version and TLS in cleartext before anything else; a
                # mismatch is answered with a stated rejection, not a silent drop.
                negotiation = handshake.negotiate_server(
                    conn, require_tls=use_tls, supports_tls=use_tls,
                    version=protocol.PROTOCOL_VERSION,
                    certfile=constants.TLS_CERT, keyfile=constants.TLS_KEY)
                if not negotiation.ok:
                    logger.warning(f'Rejected connection from {address}: {negotiation.reason}')
                    try:
                        conn.close()
                    except OSError:
                        pass
                    continue
                conn = negotiation.sock

                client = handler.Client(conn, address, clients, lambda: stop_flag)
                clients.append(client)
                client.request_nickname()

                # Inform the new client's room of the arrival
                logger.debug('Informing the room of the incoming connection.')
                client.notify_room(client.room)

                # Start Handling Thread For Client
                thread = threading.Thread(target=client.handle, name=client.id[:8])
                thread.start()
            except Exception as e:
                logger.warning(f'Dropping connection from {address}: {e}')
                # Don't leave a half-set-up client in the list; a closed socket there
                # would break every later broadcast with a bad file descriptor.
                if client is not None:
                    client.discard()
                else:
                    try:
                        conn.close()
                    except OSError:
                        pass
    except KeyboardInterrupt:
        logger.info('User stopped server manually. Enabling stop flag.')
        stop_flag = True
        sys.exit()


if __name__ == '__main__':
    serve()
