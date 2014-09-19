import os
import sys
import socket
import thread
import logging
from logging import handlers

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy_declarative

import fileDownloader.download_exception
from daemon import Daemon
from fileDownloader.downloader import DownloaderService
from sender.sender import receive_answer


engine = sqlalchemy.create_engine('sqlite:///downloads_storage.db')


HOST = ''   # Symbolic name meaning all available interfaces
PORT = 8888 # Arbitrary non-privileged port


FILE_DIR = os.getcwd()
DOWNLOAD_DIR =  os.path.join(FILE_DIR, 'server/', 'fileDownloader/' , 'downloads/')
PID_FILE = os.path.join(FILE_DIR, 'server/', 'daemon-example.pid')


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
            thread.start_new_thread(self._clientthread ,(conn,))
        self.sock.close()
 
    def _clientthread(self, conn):
        self.log.info('New thread')
        try:
            self.log.info('TRY TO GET REQUEST')
            msg = receive_answer(conn)
            self.log.info('AFTER TRY')
            self.log.info(msg)
            answer = self.performance_messages_request(msg)
            conn.close()
        except Exception:
            self.log.info('Exception in processing request')
            import traceback
            print traceback.format_exc()

    def performance_messages_request(self, msg):
        """
        Decode message,
        run appropriate function and
        get answer from request handler
        """
        if msg['command'] == ADD_URL:
            url = msg['url']
            message_answer = self.put_url_to_download_queue(url)
        elif msg['command'] == STATUS:
            message_answer = self.get_download_status()
        elif msg['command'] == DEL_FILE:
            url_id = msg['id']
            message_answer = self.delete_downloading_file(url_id)
        return message_answer

    def put_url_to_download_queue(self, url):
        message_answer = {}
        self.log.info('url: {}'.format(url))
        try:
            self.downloader = DownloaderService(url, DOWNLOAD_DIR)
            answer = False
            self.log.info('START DOWNLOAD')
            new_id = self.downloader.getId()
            self.log.info(' NEW ID = %s', new_id)
            self.download_file()
        except fileDownloader.download_exception.HTTPException:
            answer = False
            self.log.info('HTTP exception')
        except fileDownloader.download_exception.URLException:
            answer = False
            self.log.info('URL exception')
        except fileDownloader.download_exception.NoContentLengthException:
            answer = False
            self.log.info('Content-length exception')
        except fileDownloader.download_exception.CanntCreateFileError:
            answer = False
            self.log.info('Cann\'t create file error')
        except fileDownloader.download_exception.DBError:
            answer = False
            self.log.info('Problem with database')
        except:
            answer = False
            self.log.info('Some another error')
        if not answer:
            message_answer['start_download'] = 'False'
            message_answer['url_id'] = 'ERROR_DESCRIPTION'
        elif answer:
            message_answer['start_download'] = 'True'
            message_answer['url_id'] = new_id

        return message_answer

    def download_file(self):
        THREADS.append(self.downloader)
        self.downloader.start()
        self.log.info('In progress')
        self.log.info('          ')

    def get_download_status(self):
        pass

    def delete_downloading_file(self, id_to_remove):
        DBSession = sqlalchemy.orm.sessionmaker(bind=engine)
        session = DBSession()
        session.query(sqlalchemy_declarative.DownStorage).filter_by(id = id_to_remove).delete()
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