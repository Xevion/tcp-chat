"""One place to configure logging for both the server and the client.

Call :func:`configure` once at startup instead of scattering ``basicConfig``
calls across modules. Modules just ``logging.getLogger(__name__)`` and inherit
the root level and format set here, so verbosity is controlled from a single
switch and an optional log file can be turned on without touching any module.
"""

import logging

DEFAULT_FORMAT = '[%(asctime)s] [%(levelname)s] [%(threadName)s] [%(name)s] %(message)s'


def configure(level: int = logging.INFO, logfile: str = None) -> None:
    """Reset root logging to a console handler (and optional file) at ``level``.

    Safe to call more than once: existing handlers are cleared first, so repeated
    calls don't stack duplicate output. (Python 3.7 lacks ``basicConfig(force=)``,
    hence the manual reset.)
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(DEFAULT_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    root.setLevel(level)
