from PyQt5.QtCore import QThread, pyqtSignal

from client.core import ClientCore


class ReceiveWorker(QThread):
    """Pump the Qt-free core's event stream onto the Qt event loop as a signal.

    All the socket and protocol work lives in the core; this thread only carries
    each :class:`client.core.Event` across to the GUI thread, so there is nothing
    here to keep in sync with the connection logic.
    """
    event = pyqtSignal(object)

    def __init__(self, core: ClientCore, parent=None):
        QThread.__init__(self, parent)
        self.core = core
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self):
        for event in self.core.events():
            if not self._running:
                break
            self.event.emit(event)
