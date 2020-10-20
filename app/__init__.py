import datetime
import sqlalchemy
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_bootstrap import Bootstrap
from flask_jsglue import JSGlue
from flask_dropzone import Dropzone
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler

from config import *
from .db import Base, Page, PageState

engine = create_engine(database_url, convert_unicode=True)

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

Base.query = db_session.query_property()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(processing_timeout, 'interval', seconds=60)

    Path(app.config['PROCESSED_REQUESTS_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['MODELS_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['UPLOAD_IMAGES_FOLDER']).mkdir(parents=True, exist_ok=True)

    init_db()
    Bootstrap(app)
    Dropzone(app)

    jsglue = JSGlue()
    jsglue.init_app(app)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    return app


def init_db():
    from app.db import Base
    Base.metadata.create_all(bind=engine)


def processing_timeout():
    now = datetime.datetime.now()
    delta = datetime.timedelta(seconds=60)
    timestamp = now - delta

    pages = db_session.query(Page).filter(Page.state == PageState.PROCESSING).filter(Page.processing_timestamp < timestamp).all()
    for page in pages:
        page.state = PageState.WAITING
        page.processing_timestamp = None

    db_session.commit()
