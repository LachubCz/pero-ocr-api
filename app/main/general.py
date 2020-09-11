from sqlalchemy import func

from app.db.model import Request, Engine, Page, PageState
from app import db_session


def request_exists(request_id):
    request = db_session.query(Request).filter(Request.id == request_id).first()
    if request is not None:
        return True
    else:
        return False


def process_request(json_request):
    engine = db_session.query(Engine).filter(Engine.id == int(json_request["configuration"])).first()
    if engine is not None:
        request = Request(engine.id)
        db_session.add(request)
        db_session.commit()
        for image_name in json_request["images"]:
            page = Page(image_name, json_request["images"][image_name], request.id)
            db_session.add(page)
        db_session.commit()
        return request
    return None


def get_document_status(request_id):
    waiting = db_session.query(Page).filter(Page.request_id == request_id).filter(Page.state == PageState.WAITING).count()
    processed = db_session.query(Page).filter(Page.request_id == request_id).filter(Page.state == PageState.PROCESSED).count()
    status = processed / (processed + waiting)

    quality = db_session.query(func.avg(Page.score)).filter(Page.request_id == request_id).filter(Page.state == PageState.PROCESSED).first()[0]

    return status, quality
