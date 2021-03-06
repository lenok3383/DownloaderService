import urllib2
import os
import threading
import logging
from logging import handlers
import time

import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.orm
import sqlalchemy_declarative

from sqlalchemy_declarative import DownStorage as downloads_table

import download_exception


FILE_DIR = os.getcwd()
DOWNLOAD_DIR =  os.path.join(FILE_DIR, 'server', 'fileDownloader', 'downloads')
engine = sqlalchemy.create_engine('sqlite:///downloads_storage.db')
sqlalchemy_declarative.Base.metadata.bind = engine


LOG_FILE =  os.path.join(FILE_DIR, 'server', 'fileDownloader', 'downloader.log')
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


PID_FILE = os.path.join(FILE_DIR, 'server','fileDownloader', 'daemon-example.pid')


class DownloaderService(threading.Thread):

    DOWNLOAD_COMPLITE = 'download complete'
    CAN_NOT_DOWNLOAD = 'cannt download'
    FILE_ERROR = 'error with file'
    IN_PROGRESS = 'download in progress'

    def __init__(self, url, destination_path):
        super(DownloaderService, self).__init__(group=None)
        self._url_value = None
        self._speed = None
        self._size = None
        self._download_size = None
        self.url = url
        self.destination_path = destination_path
        self.log = get_logger()
        self.kill_received = False
        self.file_size = self.get_connection_with_url()
        self.new_id = self.add_new_record_to_db()
        self.create_file()

    def run(self):
        self.file_download()

    def get_connection_with_url(self):
        try:
            self.log.info('Try open url')
            self.open_url = urllib2.urlopen(self.url)
            meta = self.open_url.info()
            self.log.info('Get file size')
            file_size = int(meta.getheaders("Content-Length")[0])
            self.log.info('Get file name')
            self.file_name = self.url.split('/')[-1]
        except urllib2.HTTPError:
            self.log.info('HTTPError')
            raise download_exception.HTTPException
        except urllib2.URLError:
            self.log.info('URLError')
            raise download_exception.URLException
        except:
            self.log.info('Content - length exception')
            raise download_exception.NoContentLengthException
        return file_size

    def create_file(self):
        try:
            self.log.info('Create new file')
            new_file_name =  str(self.new_id)
            self.log.info('NEW FILE NAME: %s', new_file_name)
            self.open_file = open(os.path.join(self.destination_path,
                                               new_file_name), 'wb')
        except IOError:
            self.log.info('IOError')
            raise download_exception.CanntCreateFileError
        except Exception as e:
            self.log.info('Can not create new file. Some another error')
            self.log.info(e)
            raise download_exception.SomeAnotherError

    def add_new_record_to_db(self):
        try:
            self.log.info('Connect to DB')
            connect_to_db = WorkWithDB()
            # write new record with url into database and get record id
            new_id = connect_to_db.put_new_url_to_db(self.url, self.file_name)
        except sqlalchemy.exc.SQLAlchemyError as e:
            error_description = e
            self.log.info('DBError')
            self.log.info(error_description)
            raise download_exception.DBError
        return new_id

    def file_download(self):
        try:
            connect_to_thread_db = WorkWithDB()
            self.log.info('Start download')
            downloaded_file_size = 0
            block_sz = 8192
            download_complete = False

            start_time = time.time()
            self.log.info('START TIME: %s', start_time)
            totalSizeInKiloBytes = self.file_size / 1024
            self.log.info('Total Size In KiloBytes: %s', totalSizeInKiloBytes)
            self._url_value = self.url
            while not self.kill_received and not download_complete:
                buffer = self.open_url.read(block_sz)
                if not buffer:
                    break

                downloaded_file_size += len(buffer)
                self.open_file.write(buffer)
                self.open_file.flush()

                elapsed_time = time.time() - start_time
                self.log.info('ELAPSED TIME: %s', elapsed_time)
                speed = totalSizeInKiloBytes / elapsed_time
                self._speed = speed
                self.log.info('SPEED: %s', speed)
                self._size = self.file_size
                self._download_size = downloaded_file_size

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
            # update url download status in database
            connect_to_thread_db.update_url_status(self.new_id, self.download_status)

        except sqlalchemy.exc.SQLAlchemyError as e:
            error_description = e
            self.log.info('DBError')
            self.log.info(error_description)
        except (IOError, urllib2.HTTPError) as e:
            error_description = e
            self.log.info('Error with file')
            self.log.info(error_description)
            status = self.FILE_ERROR
            connect_to_thread_db.update_url_status(self.new_id, status)
        except Exception as e:
            status = e
            self.log.info(status)
            connect_to_thread_db.update_url_status(self.new_id, status)
        finally:
            self.open_file.close()

    @property
    def url_value(self):
        return self._url_value

    @property
    def speed(self):
        return self._speed

    @property
    def size(self):
        return self._size

    @property
    def download_size(self):
        return self._download_size

    def getId(self):
        return self.new_id


class WorkWithDB(object):

    START_DOWNLOAD = 'start download'

    def __init__(self):
        self.session = self.session_maker()

    def session_maker(self):
        DBSession = sqlalchemy.orm.sessionmaker(bind=engine)
        session = DBSession()
        return session

    def put_new_url_to_db(self, url, file_name):
        new_url = sqlalchemy_declarative.DownStorage(url=url, status=self.START_DOWNLOAD, file_name = file_name)
        self.session.add(new_url)
        self.session.commit()
        self.session.refresh(new_url)
        self.new_id = new_url.id
        return self.new_id

    def update_url_status(self, url_id, status_value):
        stmt = sqlalchemy.update(downloads_table).where(downloads_table.id == url_id).\
               values(status=status_value)
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