import os
import shutil
import datetime
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_bootstrap import Bootstrap
from flask_jsglue import JSGlue
from flask_dropzone import Dropzone
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler

from config import *
from .db import Base, Page, PageState, Request, Notification

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
    scheduler.add_job(old_files_removals, 'interval', hours=24)

    Path(app.config['PROCESSED_REQUESTS_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['MODELS_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['UPLOAD_IMAGES_FOLDER']).mkdir(parents=True, exist_ok=True)

    init_db()
    Bootstrap(app)
    Dropzone(app)

    notification = db_session.query(Notification).first()
    if notification is not None:
        notification.last_notification = datetime.datetime(1970, 1, 1)
    else:
        notification = Notification(datetime.datetime(1970, 1, 1))
        db_session.add(notification)

    db_session.commit()

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


def old_files_removals():
    now = datetime.datetime.now()
    delta = datetime.timedelta(days=7)
    timestamp = now - delta

    pages = db_session.query(Page).outerjoin(Request)\
                      .filter(Request.finish_timestamp < timestamp)\
                      .all()
    for page in pages:
        page.state = PageState.EXPIRED

    db_session.commit()

    requests = db_session.query(Request).filter(Request.finish_timestamp < timestamp).all()

    for request in requests:
        requests_dir_path = os.path.join(Config.PROCESSED_REQUESTS_FOLDER, str(request.id))
        images_dir_path = os.path.join(Config.UPLOAD_IMAGES_FOLDER, str(request.id))
        if os.path.isdir(requests_dir_path):
            shutil.rmtree(requests_dir_path)
        if os.path.isdir(images_dir_path):
            shutil.rmtree(images_dir_path)
