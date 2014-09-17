import urllib2
import os
from download_exception import HTTPException
from download_exception import URLException
from download_exception import NoContentLengthException
from download_exception import CanntCreateFileError
from download_exception import SomeAnotherError
from download_exception import DBError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy_declarative import Base
from sqlalchemy_declarative import DownStorage
from sqlalchemy import update
from urllib2 import URLError
from urllib2 import HTTPError
import threading
import sqlalchemy.exc
import logging
from logging import handlers

FILE_DIR = os.getcwd()
DOWNLOAD_DIR =  os.path.join(FILE_DIR, 'server/', 'fileDownloader/' ,
                             'downloads/','test.txt')
engine = create_engine('sqlite:///downloads_storage.db')
Base.metadata.bind = engine
FILE_DIR = os.getcwd()

LOG_FILE =  os.path.join(FILE_DIR, 'server/', 'fileDownloader/', 'downloader.log')
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

PID_FILE = os.path.join(FILE_DIR, 'server/','fileDownloader/', 'daemon-example.pid')

class DownloaderService(threading.Thread):

    DOWNLOAD_COMPLITE = 'download complete'
    CAN_NOT_DOWNLOAD = 'cannt download'
    FILE_ERROR = 'IOError'
    _cache = {}

    def __init__(self, url, destination_path):
        super(DownloaderService, self).__init__(group=None)
        self._status = None
        self.url = url
        self.destination_path = destination_path
        self.log = get_logger()
        self.kill_received = False
        self.file_size = self.get_connection_with_url()
        self.create_file()
        self.new_id = self.add_new_record_to_db()

    def run(self):
        self.file_download()

    def get_connection_with_url(self):
        try:
            self.log.info('Try open url')
            self.open_url = urllib2.urlopen(self.url)
            meta = self.open_url.info()
            self.log.info('Get file size')
            file_size = int(meta.getheaders("Content-Length")[0])
        except HTTPError:
            self.log.info('HTTPError')
            raise HTTPException
        except URLError:
            self.log.info('URLError')
            raise URLException
        except:
            self.log.info('Content - length exception')
            raise NoContentLengthException
        return file_size

    def create_file(self):
        try:
            self.log.info('Create new file')
            self.file_name = self.url.split('/')[-1]
            self.open_file = open(os.path.join(self.destination_path,
                                               self.file_name), 'wb')
        except IOError:
            self.log.info('IOError')
            raise CanntCreateFileError
        except Exception as e:
            self.log.info('Can not create new file. Some another error')
            self.log.info(e)
            raise SomeAnotherError

    def add_new_record_to_db(self):
        try:
            self.log.info('Connect to DB')
            connect_to_db = WorkWithDB()
            # write new record with url into database and get record id
            new_id = connect_to_db.put_new_url_to_db(self.url)
        except sqlalchemy.exc.IntegrityError:
            self.log.info('DBError')
            raise DBError
        return new_id

    def file_download(self):
        try:
            self.log.info('Start download')
            self.connect_to_thread_db = WorkWithDB()
            downloaded_file_size = 0
            block_sz = 8192
            download_complete = False
            while not self.kill_received and not download_complete:
                buffer = self.open_url.read(block_sz)
                if not buffer:
                    break
                downloaded_file_size += len(buffer)
                self.open_file.write(buffer)
                self.open_file.flush()
                status = {}
                status['size'] = self.file_size
                status['download_size'] = downloaded_file_size
                self._cache = status
                if downloaded_file_size == self.file_size:
                    download_complete = True
                if download_complete:
                    self.log.info('Download complete')
                    self.log.info(' ')
                    self.download_status = self.DOWNLOAD_COMPLITE
                elif self.kill_received:
                    self.log.info('Can not download file')
                    self.log.info(' ')
                    self.download_status = self.CAN_NOT_DOWNLOAD
        except IOError:
            self.log.info('IOError')
            status = self.FILE_ERROR
            self.connect_to_thread_db.update_url_status(self.new_id, status)
        except Exception as e:
            status = e
            self.log.info(status)
            self.connect_to_thread_db.update_url_status(self.new_id, status)
            print e
        finally:
            self.open_file.close()
        # update url download status in database
        self.connect_to_thread_db.update_url_status(self.new_id, self.download_status)

    @property
    def status(self):
        if self._status is None:
            self._status = self._cache
        return self._status


class WorkWithDB(object):

    START_DOWNLOAD = 'start download'

    def __init__(self):
        self.session = self.session_maker()

    def session_maker(self):
        DBSession = sessionmaker(bind=engine)
        session = DBSession()
        return session

    def put_new_url_to_db(self, url):
        new_url = DownStorage(url=url, status=self.START_DOWNLOAD)
        self.session.add(new_url)
        self.session.commit()
        self.session.refresh(new_url)
        self.new_id = new_url.id
        return self.new_id

    def update_url_status(self, url_id, status_value):
        stmt = update(DownStorage).where(DownStorage.id == url_id)\
            .values(status=status_value)
        self.session.execute(stmt)
        self.session.commit()

def get_logger():
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    file_handler = handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUPS)
    file_handler.setLevel(LOG_LEVELS.get(LOG_LEVEL, logging.DEBUG))
    file_handler.setFormatter(formatter)

    log = logging.getLogger('downloader')
    log.setLevel(LOG_LEVELS.get(LOG_LEVEL, logging.DEBUG))
    log.addHandler(file_handler)

    return log