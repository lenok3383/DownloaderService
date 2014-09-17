import logging
import socket
import sys
import os
from thread import *
from logging import handlers

from fileDownloader.downloader import DownloaderService
from fileDownloader.downloader import HTTPException
from fileDownloader.downloader import URLException
from fileDownloader.downloader import NoContentLengthException
from fileDownloader.downloader import CanntCreateFileError
from fileDownloader.downloader import SomeAnotherError
from fileDownloader.downloader import DBError
from daemon import Daemon
from sender.sender import receive_answer

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_declarative import Base, DownStorage
engine = create_engine('sqlite:///downloads_storage.db')

HOST = ''   # Symbolic name meaning all available interfaces
PORT = 8888 # Arbitrary non-privileged port

FILE_DIR = os.getcwd()

DOWNLOAD_DIR =  os.path.join(FILE_DIR, 'server/', 'fileDownloader/' , 'downloads/')

LOG_FILE =  os.path.join(FILE_DIR, 'server/', 'daemon.log')
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

PID_FILE = os.path.join(FILE_DIR, 'server/', 'daemon-example.pid')

ADD_URL = 'add_url'
STATUS = 'status'
DEL_FILE = 'delete_file'
THREADS = []

class SimpleServer(object):


    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.log = get_logger()
        self.log.info('Socket created')

    def run(self):
        self.sock.bind((HOST, PORT))
        self.log.info('Socket bind complete')
        self.sock.listen(3)
        self.log.info('Socket now listening')
        while True:
            conn, addr = self.sock.accept()
            self.log.info('Connected with ' + addr[0] + ':' + str(addr[1]))
            start_new_thread(self._clientthread ,(conn,))
        self.sock.close()
 
    def _clientthread(self, conn):
        self.log.info('New thread')
        try:
            self.log.info('TRY TO GET REQUEST')
            msg = receive_answer(conn)
            self.log.info('AFTER TRY')
            self.log.info(msg)
            answer = self.message_handler(msg)
            conn.close()
        except Exception:
            self.log.info('Exception in processing request')
            import traceback
            print traceback.format_exc()

    def message_handler(self, msg):
        if msg['command'] == ADD_URL:
            url = msg['url']
            self.put_url_to_download_queue(url)
        elif msg['command'] == STATUS:
            status = self.get_download_status()
        elif msg['command'] == DEL_FILE:
            url_id = msg['id']
            self.delete_downloading_file(url_id)

    def put_url_to_download_queue(self, url):
        self.log.info('url: {}'.format(url))
        try:
            self.downloader = DownloaderService(url, DOWNLOAD_DIR)
            answer = False
            self.log.info('START DOWNLOAD')
            self.download_file()
        except HTTPException:
            answer = False
            self.log.info('HTTP exception')
        except URLException:
            answer = False
            self.log.info('URL exception')
        except NoContentLengthException:
            answer = False
            self.log.info('Content-length exception')
        except CanntCreateFileError:
            answer = False
            self.log.info('Cann\'t create file error')
        except DBError:
            answer = False
            self.log.info('Problem with database')
        except:
            answer = False
            self.log.info('Some another error')
        if not answer:
            self.message_answer = (False, 'ERROR_DESCRIPTION')
        elif answer:
            self.message_answer = (True, " ' " )

        return self.message_answer

    def download_file(self):
        THREADS.append(self.downloader)
        self.downloader.start()
        self.log.info('In progress')
        self.log.info('          ')


    def get_download_status(self):
        pass

    def delete_downloading_file(self, id_to_remove):
        DBSession = sessionmaker(bind=engine)
        session = DBSession()
        session.query(DownStorage).filter_by(id = id_to_remove).delete()
        session.commit()
        # for t in THREADS:
        #     t.kill_received = True
        return id_to_remove


class MyDaemon(Daemon):
    def run(self):
        server = SimpleServer()
        log = get_logger()
        try:
            server.run()
        except socket.error , msg:
            log.error('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            sys.exit()  

def get_logger():
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    file_handler = handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUPS)
    file_handler.setLevel(LOG_LEVELS.get(LOG_LEVEL, logging.DEBUG))
    file_handler.setFormatter(formatter)

    log = logging.getLogger('socket_server')
    log.setLevel(LOG_LEVELS.get(LOG_LEVEL, logging.DEBUG))
    log.addHandler(file_handler)

    return log


def main():
    # daemon = MyDaemon(PID_FILE)
    # if len(sys.argv) == 2:
    #     if 'start' == sys.argv[1]:
    #         daemon.start()
    #     elif 'stop' == sys.argv[1]:
    #         daemon.stop()
    #     elif 'restart' == sys.argv[1]:
    #         daemon.restart()
    #     else:
    #         print("Unknown command")
    #         sys.exit(2)
    #     sys.exit(0)
    # else:
    #     print "usage: %s start|stop|restart" % sys.argv[0]
    #     sys.exit(2)
    server = SimpleServer()
    server.run()


if __name__ == '__main__':
    main()