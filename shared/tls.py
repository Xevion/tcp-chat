"""TLS helpers for optionally encrypting the client/server socket connection.

Disabled by default; enable it with constants.USE_TLS and point TLS_CERT / TLS_KEY
at a certificate and key. A self-signed development certificate works with
verification turned off on the client.
"""

import ssl
from typing import Optional


def server_context(certfile: str, keyfile: str) -> ssl.SSLContext:
    """Build an SSL context for the server, loading its certificate and private key."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    return context


def client_context(verify: bool = True, cafile: Optional[str] = None) -> ssl.SSLContext:
    """Build an SSL context for the client.

    With ``verify=False`` the server's certificate is accepted without checking,
    which is what a self-signed development certificate needs.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    if verify:
        if cafile is not None:
            context.load_verify_locations(cafile=cafile)
    else:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context
