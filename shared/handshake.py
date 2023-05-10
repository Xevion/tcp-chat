"""STARTTLS-style connection negotiation shared by the server and client.

Both ends exchange a short cleartext handshake before any TLS upgrade, so a
mismatch (wrong protocol version, TLS expected but not offered, and so on) comes
back as a *stated* rejection the client can show, instead of an opaque socket
reset. Only after the server says WELCOME does either side wrap the socket in
TLS, at which point the normal framed protocol takes over.

    client -> HELLO   {version, tls}
    server -> WELCOME {tls}   (then both upgrade if tls)   | REJECT {reason}

Like any STARTTLS scheme the cleartext prelude is open to an active
man-in-the-middle stripping the upgrade; that is an accepted trade-off here. The
prelude carries only a version number and a boolean, never anything secret.
"""

import socket
from typing import NamedTuple, Optional

from shared import constants
from shared import protocol
from shared import tls

HANDSHAKE_TIMEOUT = 10.0  # seconds either end will wait for the other's handshake frame


class HandshakeResult(NamedTuple):
    ok: bool
    sock: Optional[socket.socket]
    reason: str = ''
    rejected: bool = False  # True when the server stated a refusal, so retrying is pointless
    probe: bool = False  # True when the client announced this as a reachability probe


def negotiate_client(sock: socket.socket, want_tls: bool, version: int,
                     verify: bool = False, server_hostname: Optional[str] = None,
                     timeout: float = HANDSHAKE_TIMEOUT, is_probe: bool = False) -> HandshakeResult:
    """Run the client side of the handshake, returning the (maybe upgraded) socket.

    Never raises: a refusal or transport error comes back as ``ok=False`` with a
    human-readable ``reason``. A shorter ``timeout`` keeps a reachability probe
    from blocking for the full handshake window on an unresponsive peer.
    ``is_probe`` marks the HELLO as a reachability check so the server can answer
    and hang up cleanly instead of building a client it will never hear from.
    """
    previous_timeout = sock.gettimeout()
    sock.settimeout(timeout)
    try:
        sock.sendall(protocol.encode(
            {'type': constants.Types.HELLO, 'version': version,
             'tls': bool(want_tls), 'probe': bool(is_probe)}))
        reply = protocol.read_message(sock)
    except (OSError, ValueError) as e:
        return HandshakeResult(False, None, f'handshake failed: {e}')
    finally:
        try:
            sock.settimeout(previous_timeout)
        except OSError:
            pass

    if reply.get('type') == constants.Types.REJECT:
        return HandshakeResult(False, None, reply.get('reason', 'connection rejected'), rejected=True)
    if reply.get('type') != constants.Types.WELCOME:
        return HandshakeResult(False, None, 'server sent an unexpected handshake reply')

    if reply.get('tls'):
        try:
            context = tls.client_context(verify=verify)
            sock = context.wrap_socket(sock, server_hostname=server_hostname)
        except OSError as e:  # ssl.SSLError is an OSError subclass
            return HandshakeResult(False, None, f'TLS upgrade failed: {e}')

    return HandshakeResult(True, sock)


def negotiate_server(sock: socket.socket, require_tls: bool, supports_tls: bool, version: int,
                     certfile: Optional[str] = None, keyfile: Optional[str] = None) -> HandshakeResult:
    """Run the server side of the handshake against one freshly accepted socket.

    Validates the client's HELLO and either replies WELCOME (upgrading to TLS
    when both sides agree) or REJECT with a stated reason. Never raises.
    """
    previous_timeout = sock.gettimeout()
    sock.settimeout(HANDSHAKE_TIMEOUT)
    try:
        hello = protocol.read_message(sock)
    except (OSError, ValueError) as e:
        return HandshakeResult(False, None, f'handshake failed: {e}')
    finally:
        try:
            sock.settimeout(previous_timeout)
        except OSError:
            pass

    is_probe = bool(hello.get('probe'))
    reason = _refusal(hello, require_tls, supports_tls, version)
    if reason is not None:
        try:
            sock.sendall(protocol.encode({'type': constants.Types.REJECT, 'reason': reason}))
        except OSError:
            pass
        return HandshakeResult(False, None, reason, probe=is_probe)

    upgrade = bool(hello.get('tls')) and supports_tls
    try:
        sock.sendall(protocol.encode({'type': constants.Types.WELCOME, 'tls': upgrade}))
        if upgrade:
            assert certfile is not None and keyfile is not None, \
                'TLS was offered without a configured certificate and key'
            context = tls.server_context(certfile, keyfile)
            sock = context.wrap_socket(sock, server_side=True)
    except OSError as e:  # ssl.SSLError is an OSError subclass
        return HandshakeResult(False, None, f'TLS upgrade failed: {e}', probe=is_probe)

    return HandshakeResult(True, sock, probe=is_probe)


def _refusal(hello: dict, require_tls: bool, supports_tls: bool, version: int) -> Optional[str]:
    """Return a rejection reason for this HELLO, or None if it should be accepted."""
    if hello.get('type') != constants.Types.HELLO:
        return 'expected a HELLO to open the connection'
    if hello.get('version') != version:
        return f"unsupported protocol version {hello.get('version')} (server speaks {version})"
    wants_tls = bool(hello.get('tls'))
    if require_tls and not wants_tls:
        return 'server requires TLS'
    if wants_tls and not supports_tls:
        return 'server does not support TLS'
    return None
