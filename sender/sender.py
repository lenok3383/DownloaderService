import struct
import pickle
import os

from project_exception.exception import BrokenConnection

FILE_DIR = os.getcwd()
MSGTITLELEN = 4

def send_msg(conn, msg):
    msg_body = pickle.dumps(msg)
    msg_size = len(msg_body)
    title_to_send = struct.pack('!I', msg_size)
    send_message_to_socket(conn, MSGTITLELEN, title_to_send)
    send_message_to_socket(conn, msg_size, msg_body)

def send_message_to_socket(conn, length, msg):
    totalsent = 0
    while totalsent < length:
        send_msg = conn.send(msg[totalsent:])
        if not send_msg:
            raise BrokenConnection
        totalsent = totalsent + send_msg

def receive_answer(conn):
    unpack_msg_size = receive_message_from_socket(conn,
                                                  MSGTITLELEN)
    path = os.path.join(FILE_DIR, 't.txt')
    with open(path, "w") as f:
        f.write(unpack_msg_size)
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