from PyQt5.QtWidgets import QApplication
from client.gui import MainWindow

app = QApplication([])
app.setApplicationName("TCPChat Client")
m = MainWindow()

app.exec_()
