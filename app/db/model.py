import enum
import uuid
import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy import Column, Enum, ForeignKey, Integer, String, DateTime, Float
from app.db import Base

from app.db.guid import GUID


class RequestState(enum.Enum):
    NEW = 'Request created.'
    WAITING_FOR_PROCESSING = 'Waiting on start of processing.'
    RUNNING_OCR = 'Running OCR.'
    DONE = 'Request completed.'
    FAILED = 'Request failed.'
    CANCELED = 'Request canceled.'


class PageState(enum.Enum):
    CREATED = 'Page was created.'
    WAITING = 'Page is waiting for processing.'
    PROCESSING = 'Page is being processed.'
    NOT_FOUND = 'Page image was not found.'
    INVALID_FILE = 'Page image is invalid.'
    PROCESSING_FAILED = 'Page processing failed.'
    PROCESSED = 'Page was processed.'
    CANCELED = 'Page processing was canceled.'


class Permission(enum.Enum):
    SUPER_USER = 'User can take and process requests.'
    USER = 'User can create requests.'


class ApiKey(Base):
    __tablename__ = 'api_key'
    id = Column(Integer(), primary_key=True)
    api_string = Column(String(), nullable=False, index=True)
    owner = Column(String(), nullable=False)
    permission = Column(Enum(Permission), nullable=False)

    def __init__(self, api_string, owner, permission):
        self.api_string = api_string
        self.owner = owner
        self.permission = permission


class Request(Base):
    __tablename__ = 'request'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    creation_timestamp = Column(DateTime(), nullable=False, default=datetime.datetime.utcnow)
    modification_timestamp = Column(DateTime(), nullable=False, default=datetime.datetime.utcnow)
    finish_timestamp = Column(DateTime(), nullable=True)

    engine_id = Column(Integer(), ForeignKey('engine.id'), nullable=False)
    api_key_id = Column(Integer(), ForeignKey('api_key.id'), nullable=False)

    #pages = relationship('Page', back_populates="request", lazy='dynamic')

    def __init__(self, engine_id, api_key_id):
        self.engine_id = engine_id
        self.api_key_id = api_key_id


class Page(Base):
    __tablename__ = 'page'
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(), nullable=False)
    url = Column(String(), nullable=False)
    state = Column(Enum(PageState), nullable=False, index=True, default=PageState.WAITING)
    score = Column(Float(), nullable=True)
    traceback = Column(String(), nullable=True)
    finish_timestamp = Column(DateTime(), nullable=True)

    request_id = Column(GUID(), ForeignKey('request.id'), nullable=False, index=True)
    engine_version = Column(Integer(), ForeignKey('engine_version.id'), nullable=True)

    def __init__(self, name, url, request_id):
        self.name = name
        self.url = url
        self.request_id = request_id


class Engine(Base):
    __tablename__ = 'engine'
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
    id = Column(Integer(), primary_key=True)
    version = Column(String(), nullable=False)
    config_path = Column(String(), nullable=False)
    description = Column(String(), nullable=True)
    engine_id = Column(Integer(), ForeignKey('engine.id'), nullable=False)

    #pages = relationship('Page', back_populates="engine_version", lazy='dynamic')

    def __init__(self, version, config_path, engine_id, description=None):
        self.version = version
        self.config_path = config_path
        self.engine_id = engine_id
        self.description = description


class EngineVersionModel(Base):
    __tablename__ = 'engine_version_model'
    id = Column(Integer(), primary_key=True)
    engine_version_id = Column(Integer(), ForeignKey('engine_version.id'), nullable=False)
    model_id = Column(Integer(), ForeignKey('model.id'), nullable=False)

    def __init__(self, engine_version_id, model_id):
        self.engine_version_id = engine_version_id
        self.model_id = model_id


class Model(Base):
    __tablename__ = 'model'
    id = Column(Integer(), primary_key=True)
    name = Column(String(), nullable=False)
    path = Column(String(), nullable=False)

    def __init__(self, name, path):
        self.name = name
        self.path = path


if __name__ == '__main__':
    engine = create_engine('sqlite:///{}'.format('C:/Users/LachubCz_NTB/Documents/GitHub/PERO-API/app/database.db'),
                           convert_unicode=True,
                           connect_args={'check_same_thread': False})
    db_session = scoped_session(sessionmaker(autocommit=False,
                                             autoflush=False,
                                             bind=engine))
    Base.query = db_session.query_property()
    Base.metadata.create_all(bind=engine)

    pages = db_session.query(Page).all()

    engine_1 = Engine('Engine_1', 'description')
    db_session.add(engine_1)
    db_session.commit()

    engine_version_1_1 = EngineVersion('v0.0.1', 'C:\\Users\\LachubCz_NTB\\Documents\\GitHub\\PERO-API\\processing_client\\engines\\example_config.ini', engine_1.id)
    db_session.add(engine_version_1_1)
    db_session.commit()

    engine_2 = Engine('Engine_2', 'description')
    db_session.add(engine_2)
    db_session.commit()

    engine_version_2_1 = EngineVersion('v0.0.1', 'C:\\Users\\LachubCz_NTB\\Documents\\GitHub\\PERO-API\\processing_client\\engines\\example_config.ini', engine_2.id)
    db_session.add(engine_version_2_1)
    db_session.commit()

    engine_version_1_2 = EngineVersion('v0.0.2', 'C:\\Users\\LachubCz_NTB\\Documents\\GitHub\\PERO-API\\processing_client\\engines\\example_config.ini', engine_1.id)
    db_session.add(engine_version_1_2)
    db_session.commit()

    model_1 = Model('lidove_noviny', 'C:/Users/LachubCz_NTB/Documents/GitHub/PERO-API/models/lidove_noviny/model/')
    db_session.add(model_1)
    db_session.commit()

    model_2 = Model('universal', 'C:/Users/LachubCz_NTB/Documents/GitHub/PERO-API/models/universal/model/')
    db_session.add(model_2)
    db_session.commit()

    engine_version_model_1 = EngineVersionModel(engine_version_1_1.id, model_1.id)
    db_session.add(engine_version_model_1)
    engine_version_model_2 = EngineVersionModel(engine_version_1_1.id, model_2.id)
    db_session.add(engine_version_model_2)

    engine_version_model_3 = EngineVersionModel(engine_version_2_1.id, model_1.id)
    db_session.add(engine_version_model_3)
    engine_version_model_4 = EngineVersionModel(engine_version_2_1.id, model_2.id)
    db_session.add(engine_version_model_4)

    engine_version_model_5 = EngineVersionModel(engine_version_1_2.id, model_1.id)
    db_session.add(engine_version_model_5)
    engine_version_model_6 = EngineVersionModel(engine_version_1_2.id, model_2.id)
    db_session.add(engine_version_model_6)

    api_key = ApiKey('test_user', 'Owner of The Key', Permission.SUPER_USER)
    db_session.add(api_key)
    db_session.commit()

    request = Request(engine_1.id, api_key.id)
    db_session.add(request)
    db_session.commit()

    page1 = Page('Magna_Carta', 'https://upload.wikimedia.org/wikipedia/commons/e/ee/Magna_Carta_%28British_Library_Cotton_MS_Augustus_II.106%29.jpg', request.id)
    db_session.add(page1)
    page2 = Page('United_States_Declaration_of_Independence', 'https://upload.wikimedia.org/wikipedia/commons/8/8f/United_States_Declaration_of_Independence.jpg', request.id)
    db_session.add(page2)
    db_session.commit()

    page1.state = PageState.PROCESSED
    page1.score = 86.7
    db_session.commit()

    request = Request(engine_2.id, api_key.id)
    db_session.add(request)
    db_session.commit()

    page1 = Page('Magna_Carta', 'https://upload.wikimedia.org/wikipedia/commons/e/ee/Magna_Carta_%28British_Library_Cotton_MS_Augustus_II.106%29.jpg', request.id)
    db_session.add(page1)
    page2 = Page('United_States_Declaration_of_Independence', 'https://upload.wikimedia.org/wikipedia/commons/8/8f/United_States_Declaration_of_Independence.jpg', request.id)
    db_session.add(page2)
    db_session.commit()
