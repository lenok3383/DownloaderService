import socket
import os
import logging
from logging import handlers
import traceback

from project_exception.exception import BrokenConnection
from sender.sender import send_msg
from sender.sender import receive_answer


ADD_URL = 'add_url'
STATUS = 'status'
DEL_FILE = 'delete_file'

FILE_DIR = os.getcwd()


LOG_FILE =  os.path.join(FILE_DIR, 'client/', 'client.log')
LOG_FORMAT = '%(levelname)s:%(name)s: %(message)s (%(asctime)s; %(filename)s:%(lineno)d)'
LOG_MAX_SIZE = 10000000
LOG_BACKUPS = 5
LOG_LEVEL = 'DEBUG'
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARN': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL}


class ClientSocket(object):

    def __init__(self, sock=None):
        if not sock:
            self.sock = socket.socket(
                        socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
        self.log = get_logger()
        self.connect = self.connect('localhost', 8888)
        self.log.info('Socket now listening')

    def connect(self, host, port):
        try:
            self.sock.connect((host, port))
            self.log.info('Establish connection')
        except socket.error as msg:
            self.log.info('Socket error')
            self.log.info(traceback.format_exc())
            raise BrokenConnection

    def send_add_url(self):
        data = raw_input ( "TYPE URL:" )
        self.log.info('URL: %s', data)
        send_cmd = {}
        send_cmd['command'] = ADD_URL
        send_cmd['url'] = data
        self.log.info('Message with ADD URL: %s', send_cmd)
        send_msg(self.sock, send_cmd)

    def receive_download_status(self):
        answer = receive_answer(self.sock)
        self.log.info('Answer with download status: %s', answer)
        if  not answer['start_download']:
            print answer['error_text']
            url_id = 0
        elif answer['start_download']:
            url_id = answer['url_id']
        self.log.info('Url id = %s', url_id)
        return url_id

    def send_request_to_delete(self, id):
        send_cmd = {}
        send_cmd['command'] = DEL_FILE
        send_cmd['id'] = id
        send_msg(self.sock, send_cmd)

    def receive_deleted_download_id(self):
        answer = receive_answer(self.sock)
        self.log.info('Answer with deleted download id: %s', answer)
        if answer['id']:
            url_id = answer['id']
        self.log.info('Deleted url id = %s', url_id)
        return  url_id


def get_logger():
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    file_handler = handlers.RoltatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUPS)
    file_handler.setLevel(LOG_LEVELS.get(LOG_LEVEL, logging.DEBUG))
    file_handler.setFormatter(formatter)

    log = logging.getLogger('client_server')
    log.setLevel(LOG_LEVELS.get(LOG_LEVEL, logging.DEBUG))
    log.addHandler(file_handler)

    return log

def main():
    conn = ClientSocket()
    log = get_logger()
    log.info('Send url to server')
    conn.send_add_url()
    url_id = conn.receive_download_status()

    conn_to_del = ClientSocket()
    log.info('Send id to delete')
    if url_id:
        url_id -= 1
        conn_to_del.send_request_to_delete(url_id)
    conn_to_del.receive_deleted_download_id()


if __name__ == '__main__':
    main()