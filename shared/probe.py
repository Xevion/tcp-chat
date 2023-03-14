"""Quick reachability check used by the client's Test Connection button.

Opens a short-lived connection to a host/port (optionally over TLS) just to see
whether the server answers, then closes it. No protocol messages are exchanged,
so it is cheap enough to fire on a button press and report back rapidly.
"""

import socket
from typing import NamedTuple

from shared import tls


class ProbeResult(NamedTuple):
    ok: bool
    detail: str


def probe_connection(host: str, port: int, use_tls: bool = False,
                     verify: bool = False, timeout: float = 3.0) -> ProbeResult:
    """Attempt to reach host:port within timeout seconds. Never raises."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        if use_tls:
            sock = tls.client_context(verify=verify).wrap_socket(sock, server_hostname=host)
        sock.connect((host, port))
        return ProbeResult(True, 'Connection succeeded.')
    except socket.timeout:
        return ProbeResult(False, 'Connection timed out.')
    except OSError as e:
        return ProbeResult(False, str(e))
    finally:
        sock.close()
