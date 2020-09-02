from app.db import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import Column, Enum, ForeignKey, Integer, String
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


class ApiKey(Base):
    __tablename__ = 'api_key'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer(), primary_key=True)
    api_string = Column(String(), nullable=False)
    owner = Column(String(), nullable=False)
    permission = Column(Integer(), nullable=False)


class Request(Base):
    __tablename__ = 'request'
    __table_args__ = {'extend_existing': True}
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    state = Column(Enum(RequestState), nullable=False)

    pages = relationship('Page', back_populates="request", lazy='dynamic')

class Page(Base):
    __tablename__ = 'page'
    __table_args__ = {'extend_existing': True}
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(), nullable=False)
    path = Column(String(), nullable=False)
    request_id = Column(GUID(), ForeignKey('request.id'), nullable=False)


class Engine(Base):
    __tablename__ = 'engine'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer(), primary_key=True)
    name = Column(String(), nullable=False)

    versions = relationship('EngineVersion', back_populates="engine", lazy='dynamic')

class EngineVersion(Base):
    __tablename__ = 'engine_version'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer(), primary_key=True)
    version = Column(String(), nullable=False)
    engine_id = Column(Integer, ForeignKey('engine.id'), nullable=False)


if __name__ == '__main__':
    engine = create_engine('sqlite:///{}'.format('database.db'),
                           convert_unicode=True,
                           connect_args={'check_same_thread': False})
    db_session = scoped_session(sessionmaker(autocommit=False,
                                             autoflush=False,
                                             bind=engine))
    Base.query = db_session.query_property()
    Base.metadata.create_all(bind=engine)
