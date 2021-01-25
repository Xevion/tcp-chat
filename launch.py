import sys

from faker import Faker

if __name__ == "__main__":
    arg_count = len(sys.argv) - 1
    if arg_count < 1:
        print('Please provide one argument besides the file describing whether to launch the client or server.')
        print('Client/C/1 to launch the client. Server/S/2 to launch the server.')
    else:
        if str(sys.argv[1]).lower() in ['client', 'c', '1']:
            nick = None
            if arg_count >= 2:
                if sys.argv[2] == 'random':
                    fake = Faker()
                    nick = fake.user_name()
                else:
                    nick = sys.argv[2]

            from client.main import main
            main(nick)
        elif str(sys.argv[1]).lower() in ['server', 's', '2']:
            from server import main
            main.receive()
