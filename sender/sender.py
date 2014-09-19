import struct
import pickle
import os
import logging
from logging import handlers

from project_exception.exception import BrokenConnection

FILE_DIR = os.getcwd()

LOG_FILE =  os.path.join(FILE_DIR, 'sender', 'sender.log')
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


PID_FILE = os.path.join(FILE_DIR, 'sender','sender.pid')


MSGTITLELEN = 4

def send_msg(conn, msg):
    log = get_logger()
    msg_body = pickle.dumps(msg)
    msg_size = len(msg_body)
    log.info('Msg size: %s', msg_size)
    title_to_send = struct.pack('!I', msg_size)
    send_message_to_socket(conn, MSGTITLELEN, title_to_send)
    send_message_to_socket(conn, msg_size, msg_body)

def send_message_to_socket(conn, length, msg):
    log = get_logger()
    log.info('Message length: %s', length)
    totalsent = 0
    while totalsent < length:
        send_msg = conn.send(msg[totalsent:])
        log.info('Totalsent in while: %s', totalsent)
        if not send_msg:
            log.info('BrokenConnection')
            raise BrokenConnection
        totalsent = totalsent + send_msg

def receive_answer(conn):
    log = get_logger()
    unpack_msg_size = receive_message_from_socket(conn,
                                                  MSGTITLELEN)
    length_list = struct.unpack('!I', unpack_msg_size)
    msg_lenght = length_list[0]
    pikle_data =  receive_message_from_socket(conn,
                                              msg_lenght)
    data = pickle.loads(pikle_data)
    return data
   
def receive_message_from_socket(conn, lenght):
    data_list = []
    bytes_recd = 0
    while bytes_recd < lenght:
        data = conn.recv(min(lenght - bytes_recd, 2048))
        if not  data:
            raise BrokenConnection
        bytes_recd = bytes_recd + len(data)
        data_list.append(data)
    answer = ''.join(data_list)
    return answer

def get_logger():
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    file_handler = handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUPS)
    file_handler.setLevel(LOG_LEVELS.get(LOG_LEVEL, logging.DEBUG))
    file_handler.setFormatter(formatter)

    log = logging.getLogger('sender')
    log.setLevel(LOG_LEVELS.get(LOG_LEVEL, logging.DEBUG))
    log.addHandler(file_handler)

    return log