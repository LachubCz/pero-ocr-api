import os
import datetime
import sqlalchemy
from sqlalchemy import func

from app.db.model import Request, Engine, Page, PageState, ApiKey, EngineVersion
from app import db_session
from app.wsgi import app


def request_exists(request_id):
    try:
        request = db_session.query(Request).filter(Request.id == request_id).first()
    except sqlalchemy.exc.StatementError:
        return False

    if request is not None:
        return True
    else:
        return False


def process_request(api_string, json_request):
    engine = db_session.query(Engine).filter(Engine.id == int(json_request["configuration"])).first()
    api_key = db_session.query(ApiKey).filter(ApiKey.api_string == api_string).first()
    if engine is not None:
        request = Request(engine.id, api_key.id)
        db_session.add(request)
        db_session.commit()
        for image_name in json_request["images"]:
            page = Page(image_name, json_request["images"][image_name], request.id)
            db_session.add(page)
        db_session.commit()
        return request
    return None


def get_document_status(request_id):
    not_processed = db_session.query(Page).filter(Page.request_id == request_id).filter(Page.state != PageState.PROCESSED).count()
    processed = db_session.query(Page).filter(Page.request_id == request_id).filter(Page.state == PageState.PROCESSED).count()
    status = processed / (processed + not_processed)

    quality = db_session.query(func.avg(Page.score)).filter(Page.request_id == request_id).filter(Page.state == PageState.PROCESSED).first()[0]

    return status, quality


def cancel_request_by_id(request_id):
    waiting_pages = db_session.query(Page).filter(Page.request_id == request_id).filter(Page.state != PageState.PROCESSED).all()
    for page in waiting_pages:
        page.state = PageState.CANCELED
    db_session.commit()


def get_ocr_systems():
    engines = db_session.query(Engine).all()
    engines_dict = []
    for engine in engines:
        engines_dict.append({'id': engine.id, 'name': engine.name, 'description': engine.description})

    return engines_dict


def get_page_by_id(page_id):
    page = db_session.query(Page).filter(Page.id == page_id).first()

    return page


def check_save_path(request_id):
    if not os.path.isdir(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(request_id))):
        os.mkdir(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(request_id)))


def get_page_by_preferred_engine(engine_id):
    page = db_session.query(Page).join(Request).filter(Page.state == PageState.WAITING)\
                                               .filter(Request.engine_id == engine_id).first()
    if not page:
        page = db_session.query(Page).filter(Page.state == PageState.WAITING).first()
        if page:
            engine_id = db_session.query(Request.engine_id).filter(Request.id == page.request_id).first()[0]

    if page:
        page.state = PageState.PROCESSING
        db_session.commit()

    return page, engine_id


def request_belongs_to_api_key(api_key, request_id):
    api_key = db_session.query(ApiKey).filter(ApiKey.api_string == api_key).first()
    request = db_session.query(Request).filter(Request.api_key_id == api_key.id).filter(Request.id == request_id).first()
    return request


def get_engine_version(engine_id, version_name):
    engine_version = db_session.query(EngineVersion).filter(EngineVersion.version == version_name).first()
    if not engine_version:
        engine_version = EngineVersion(version_name, engine_id)
        db_session.add(engine_version)
        db_session.commit()
    return engine_version


def get_engine_by_page_id(page_id):
    page = db_session.query(Page).filter(Page.id == page_id).first()
    request = db_session.query(Request).filter(Request.id == page.request_id).first()
    engine = db_session.query(Engine).filter(Engine.id == request.engine_id).first()

    return engine


def change_page_to_processed(page_id, score, engine_version):
    page = db_session.query(Page).filter(Page.id == page_id).first()
    request = db_session.query(Request).filter(Request.id == page.request_id).first()

    page.score = score
    page.state = PageState.PROCESSED
    page.engine_version = engine_version

    timestamp = datetime.datetime.utcnow()
    page.finish_timestamp = timestamp
    request.modification_timestamp = timestamp
    db_session.commit()
    if is_request_processed(request.id):
        request.finish_timestamp = timestamp
        db_session.commit()


def is_request_processed(request_id):
    status, _ = get_document_status(request_id)
    if status == 1.0:
        return True
    else:
        return False
