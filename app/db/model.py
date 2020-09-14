import datetime

from app.db import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import Column, Enum, ForeignKey, Integer, String, DateTime, Float
from app.db.guid import GUID
import enum
from sqlalchemy.orm import relationship
import uuid


class RequestState(enum.Enum):
    NEW = 'Request created.'
    WAITING_FOR_PROCESSING = 'Waiting on start of processing.'
    RUNNING_OCR = 'Running OCR.'
    DONE = 'Request completed.'
    FAILED = 'Request failed.'
    CANCELED = 'Request canceled.'


class PageState(enum.Enum):
    WAITING = 'Page is waiting for processing.'
    PROCESSED = 'Page was processed.'
    CANCELED = 'Page processing was canceled.'


class Permission(enum.Enum):
    SUPER_USER = 'User can take and process requests.'
    USER = 'User can create requests.'


class ApiKey(Base):
    __tablename__ = 'api_key'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer(), primary_key=True)
    api_string = Column(String(), nullable=False)
    owner = Column(String(), nullable=False)
    permission = Column(Enum(Permission), nullable=False)

    def __init__(self, api_string, owner, permission):
        self.api_string = api_string
        self.owner = owner
        self.permission = permission


class Request(Base):
    __tablename__ = 'request'
    __table_args__ = {'extend_existing': True}
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    creation_timestamp = Column(DateTime(), nullable=False, default=datetime.datetime.utcnow)
    modification_timestamp = Column(DateTime(), nullable=False, default=datetime.datetime.utcnow)
    finish_timestamp = Column(DateTime(), nullable=True)

    engine_id = Column(Integer(), ForeignKey('engine.id'), nullable=False)
    #pages = relationship('Page', back_populates="request", lazy='dynamic')

    def __init__(self, engine_id):
        self.engine_id = engine_id


class Page(Base):
    __tablename__ = 'page'
    __table_args__ = {'extend_existing': True}
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(), nullable=False)
    path = Column(String(), nullable=False)
    state = Column(Enum(PageState), nullable=False, default=PageState.WAITING)
    score = Column(Float(), nullable=True)
    finish_timestamp = Column(DateTime(), nullable=True)

    request_id = Column(GUID(), ForeignKey('request.id'), nullable=False)
    engine_version = Column(Integer(), ForeignKey('engine_version.id'), nullable=True)

    def __init__(self, name, path, request_id):
        self.name = name
        self.path = path
        self.request_id = request_id


class Engine(Base):
    __tablename__ = 'engine'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer(), primary_key=True)
    name = Column(String(), nullable=False)
    description = Column(String(), nullable=True)

    #versions = relationship('EngineVersion', back_populates="engine", lazy='dynamic')
    #requests = relationship('Request', back_populates="engine", lazy='dynamic')

    def __init__(self, name, description):
        self.name = name
        self.description = description


class EngineVersion(Base):
    __tablename__ = 'engine_version'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer(), primary_key=True)
    version = Column(String(), nullable=False)
    engine = Column(Integer(), ForeignKey('engine.id'), nullable=False)

    #pages = relationship('Page', back_populates="engine_version", lazy='dynamic')

    def __init__(self, version, engine_id):
        self.version = version
        self.engine_id = engine_id


if __name__ == '__main__':
    engine = create_engine('sqlite:///{}'.format('database.db'),
                           convert_unicode=True,
                           connect_args={'check_same_thread': False})
    db_session = scoped_session(sessionmaker(autocommit=False,
                                             autoflush=False,
                                             bind=engine))
    Base.query = db_session.query_property()
    Base.metadata.create_all(bind=engine)
