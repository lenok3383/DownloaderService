import socket

from project_exception.exception import BrokenConnection
from sender.sender import send_msg
from sender.sender import receive_answer


ADD_URL = 'add_url'
STATUS = 'status'
DEL_FILE = 'delete_file'


class ClientSocket(object):

    def __init__(self, sock=None):
        if not sock:
            self.sock = socket.socket(
                        socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
        self.connect = self.connect('localhost', 8888)
        self.send_add_url()
        url_id = self.receive_download_status()

    def connect(self, host, port):
        try:
            self.sock.connect((host, port))
        except socket.error as msg:
            raise BrokenConnection

    def send_add_url(self):
        data = raw_input ( "TYPE URL:" )
        send_cmd = {}
        send_cmd['command'] = ADD_URL
        send_cmd['url'] = data
        send_msg(self.sock, send_cmd)

    def receive_download_status(self):
        answer = receive_answer(self.sock)
        if  answer['start_download'] == False:
            print answer['error_text']
            url_id = 0
        elif answer['start_download'] == True:
            url_id = answer['url_id']
        return url_id


def main():
    ClientSocket()


if __name__ == '__main__':
    main()