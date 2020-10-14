import sqlalchemy
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_bootstrap import Bootstrap
from flask_jsglue import JSGlue
from flask_dropzone import Dropzone
from pathlib import Path

from config import *
from .db import Base

engine = create_engine(database_url, convert_unicode=True, connect_args={'check_same_thread': False})

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

Base.query = db_session.query_property()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
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
