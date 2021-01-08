from PyQt5.QtWidgets import QApplication
from client.gui import MainWindow

import socket
import threading

# nickname = input("Nickname: ")

app = QApplication([])
app.setApplicationName("TCPChat Client")
m = MainWindow()

# client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# client.connect(('127.0.0.1', 55555))
#
# def receive():
#     while True:
#         try:
#             message = client.recv(1024).decode('ascii')
#             if message == 'NICK':
#                 client.send(nickname.encode('ascii'))
#             else:
#                 m.addMessage(message)
#                 # print(message)
#         except:
#             print("Error! Disconnecting.")
#             client.close()
#             break
#
# Sending Messages To Server
# def write():
#     while True:
#         message = '{}: {}'.format(nickname, input(''))
#         client.send(message.encode('ascii'))
#
# Starting Threads For Listening And Writing
# receive_thread = threading.Thread(target=receive)
# receive_thread.start()

app.exec_()
