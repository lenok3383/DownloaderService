import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
 
Base = declarative_base()
 
class DownStorage(Base):
    __tablename__ = 'downloads'
    id = Column(Integer, primary_key=True)
    url = Column(String(250), nullable=False)
    file_name = Column(String(250), nullable=False)
    status = Column(String(250), nullable=False)
 
engine = create_engine('sqlite:///downloads_storage.db')
 
Base.metadata.create_all(engine)