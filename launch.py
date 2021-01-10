import sys

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('Please provide one argument besides the file describing whether to launch the client or server.')
        print('Client/C/1 to launch the client. Server/S/2 to launch the server.')
    else:
        if str(sys.argv[1]).lower() in ['client', 'c', '1']:
            from PyQt5.QtWidgets import QApplication
            from client.gui import MainWindow

            app = QApplication([])
            app.setApplicationName("TCPChat Client")
            m = MainWindow()
            app.exec_()
        elif str(sys.argv[1]).lower() in ['server', 's', '2']:
            from server import main
            main.receive()
