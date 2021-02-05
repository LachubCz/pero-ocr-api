import os
import os.path
import zipfile
import datetime
import traceback
from io import BytesIO
from urllib.parse import urlparse
from filelock import FileLock, Timeout
from flask import redirect, request, jsonify, send_file, abort
from flask_mail import Message, Mail
from pathlib import Path
from app.main import bp
from app.db.api_key import require_user_api_key, require_super_user_api_key
from app.db.model import PageState
from flask import current_app as app
from flask import render_template
from app.main.general import process_request, request_exists, cancel_request_by_id, \
                             get_engine_dict, get_page_by_id, check_save_path, get_page_by_preferred_engine, \
                             request_belongs_to_api_key, get_engine_version, get_engine_by_page_id, \
                             change_page_to_processed, get_page_and_page_state, get_engine, get_latest_models, \
                             get_document_pages, change_page_to_failed, get_page_statistics, change_page_path, \
                             get_request_by_page, get_notification, set_notification, get_api_key_by_id


@bp.route('/')
@bp.route('/index')
def index():
    state_stats, _ = get_page_statistics()
    return render_template('index.html', data=state_stats)


@bp.route('/docs')
def documentation():
    return redirect('https://app.swaggerhub.com/apis-docs/LachubCz/PERO-API/1.0.1')


@bp.route('/post_processing_request', methods=['POST'])
@require_user_api_key
def post_processing_request():
    api_string = request.headers.get('api-key')
    try:
        db_request = process_request(api_string, request.json)
    except:
        return jsonify({
            'status': 'failure',
            'message': 'Bad JSON format.'}), 422
    else:
        if db_request is not None:
            return jsonify({
                'status': 'success',
                'request_id': db_request.id}), 200
        else:
            return jsonify({
                'status': 'failure',
                'message': 'Engine not found.'}), 404


@bp.route('/upload_image/<string:request_id>/<string:page_name>', methods=['POST'])
@require_user_api_key
def upload_image(request_id, page_name):
    request_ = request_exists(request_id)
    if not request_:
        return jsonify({
            'status': 'failure',
            'message': 'Request doesn\'t exist.'}), 404
    if not request_belongs_to_api_key(request.headers.get('api-key'), request_id):
        return jsonify({
            'status': 'failure',
            'message': 'Request doesn\'t belong to this API key.'}), 401
    page, page_state = get_page_and_page_state(request_id, page_name)
    if not page:
        return jsonify({
            'status': 'failure',
            'message': 'Page doesn\'t exist.'}), 404
    if page_state != PageState.CREATED:
        return jsonify({
            'status': 'failure',
            'message': 'Page isn\'t in CREATED state.'}), 202

    if 'file' not in request.files:
        return jsonify({
            'status': 'failure',
            'message': 'Request file doesn\'t exists.'}), 400

    file = request.files['file']
    if file and file.filename.split('.')[-1] in app.config['ALLOWED_IMAGE_EXTENSIONS']:
        Path(os.path.join(app.config['UPLOAD_IMAGES_FOLDER'], str(page.request_id))).mkdir(parents=True, exist_ok=True)
        file.save(os.path.join(app.config['UPLOAD_IMAGES_FOLDER'], str(page.request_id), page_name+'.'+file.filename.split('.')[-1]))
        o = urlparse(request.base_url)
        path = '{}://{}{}/download_image/{}/{}'.format(o.scheme, o.netloc, app.config['APPLICATION_ROOT'], request_id, page_name+'.'+file.filename.split('.')[-1])
        change_page_path(request_id, page_name, path)
        return jsonify({
            'status': 'success'})
    else:
        return jsonify({
            'status': 'failure',
            'message': 'Bad image extension.'}), 422


@bp.route('/request_status/<string:request_id>', methods=['GET'])
@require_user_api_key
def request_status(request_id):
    if not request_exists(request_id):
        return jsonify({
            'status': 'failure',
            'message': 'Request doesn\'t exist.'}), 404

    if not request_belongs_to_api_key(request.headers.get('api-key'), request_id):
        return jsonify({
            'status': 'failure',
            'message': 'Request doesn\'t belong to this API key.'}), 401

    pages = get_document_pages(request_id)

    return jsonify({
        'status': 'success',
        'request_status': {page.name: {'state': str(page.state).split('.')[1], 'quality': page.score} for page in pages}}), 200


@bp.route('/get_engines', methods=['GET'])
@require_user_api_key
def get_engines():
    engines = get_engine_dict()
    return jsonify({
        'status': 'success',
        'engines': engines}
    )


@bp.route('/download_results/<string:request_id>/<string:page_name>/<string:format>', methods=['GET'])
@require_user_api_key
def download_results(request_id, page_name, format):
    request_ = request_exists(request_id)
    if not request_:
        return jsonify({
            'status': 'failure',
            'message': 'Request doesn\'t exist.'}), 404
    if not request_belongs_to_api_key(request.headers.get('api-key'), request_id):
        return jsonify({
            'status': 'failure',
            'message': 'Request doesn\'t belong to this API key.'}), 401
    page, page_state = get_page_and_page_state(request_id, page_name)
    if not page:
        return jsonify({
            'status': 'failure',
            'message': 'Page doesn\'t exist.'}), 404
    if page_state == PageState.EXPIRED:
        return jsonify({
            'status': 'failure',
            'message': 'Page has expired.'}), 404
    if page_state != PageState.PROCESSED:
        return jsonify({
            'status': 'failure',
            'message': 'Page isn\'t processed.'}), 202
    if format not in ['alto', 'page', 'txt']:
        return jsonify({
            'status': 'failure',
            'message': 'Bad export format.'}), 400

    lock = FileLock(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(page.request_id), str(page.request_id)+'_lock'), timeout=1)
    try:
        with lock:
            archive = zipfile.ZipFile(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(request_.id), str(request_.id)+'.zip'), 'r')
            if format == 'alto':
                data = archive.read('{}_alto.xml'.format(page.name))
                extension = 'xml'
            elif format == 'page':
                data = archive.read('{}_page.xml'.format(page.name))
                extension = 'xml'
            elif format == 'txt':
                data = archive.read('{}.txt'.format(page.name))
                extension = 'txt'
    except Timeout:
        archive = zipfile.ZipFile(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(request_.id), str(request_.id) + '.zip'), 'r')
        if format == 'alto':
            data = archive.read('{}_alto.xml'.format(page.name))
            extension = 'xml'
        elif format == 'page':
            data = archive.read('{}_page.xml'.format(page.name))
            extension = 'xml'
        elif format == 'txt':
            data = archive.read('{}.txt'.format(page.name))
            extension = 'txt'

    return send_file(BytesIO(data),
                     attachment_filename='{}.{}'.format(page.name, extension),
                     as_attachment=True)


@bp.route('/cancel_request/<string:request_id>', methods=['POST'])
@require_user_api_key
def cancel_request(request_id):
    if not request_exists(request_id):
        return jsonify({
            'status': 'failure',
            'message': 'Request doesn\'t exist.'}), 404

    if not request_belongs_to_api_key(request.headers.get('api-key'), request_id):
        return jsonify({
            'status': 'failure',
            'message': 'Request doesn\'t belong to this API key.'}), 401

    cancel_request_by_id(request_id)
    return jsonify({
        'status': 'success'}), 200


@bp.route('/get_processing_request/<int:preferred_engine_id>', methods=['GET'])
@require_super_user_api_key
def get_processing_request(preferred_engine_id):
    page, engine_id = get_page_by_preferred_engine(preferred_engine_id)

    if page:
        return jsonify({
            'status': 'success',
            'page_id': page.id,
            'page_url': page.url,
            'engine_id': engine_id}), 200
    else:
        return jsonify({
            'status': 'failure',
            'message': 'No available page for processing.'}), 404


@bp.route('/upload_results/<string:page_id>', methods=['POST'])
@require_super_user_api_key
def upload_results(page_id):
    page = get_page_by_id(page_id)
    if not page:
        return jsonify({
            'status': 'failure',
            'message': 'Page doesn\'t exist.'}), 404

    score = round(float(request.headers.get('score')) * 100, 2)
    engine_version_str = str(request.headers.get('engine-version'))

    engine = get_engine_by_page_id(page_id)
    engine_version = get_engine_version(engine.id, engine_version_str)

    check_save_path(page.request_id)

    lock = FileLock(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(page.request_id), str(page.request_id)+'_lock'), timeout=1)
    try:
        with lock:
            with zipfile.ZipFile(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(page.request_id), str(page.request_id)+'.zip'), 'a', zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr(page.name + '_alto.xml', request.files['alto'].read())
                zipf.writestr(page.name + '_page.xml', request.files['page'].read())
                zipf.writestr(page.name + '.txt', request.files['txt'].read())
    except Timeout:
        with zipfile.ZipFile(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(page.request_id), str(page.request_id) + '.zip'), 'a', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr(page.name + '_alto.xml', request.files['alto'].read())
            zipf.writestr(page.name + '_page.xml', request.files['page'].read())
            zipf.writestr(page.name + '.txt', request.files['txt'].read())

    change_page_to_processed(page_id, score, engine_version.id)

    # remove image if exists
    extension = page.url.split('.')[-1]
    page_name = page.name
    request_id = page.request_id
    image_path = os.path.join(app.config['UPLOAD_IMAGES_FOLDER'], str(request_id), '{}.{}'.format(page_name, extension))
    if os.path.isfile(image_path):
        os.remove(image_path)

    return jsonify({
        'status': 'success'}), 200


@bp.route('/download_engine/<int:engine_id>', methods=['GET'])
@require_super_user_api_key
def download_engine(engine_id):
    engine = get_engine(engine_id)
    if not engine:
        return jsonify({
            'status': 'failure',
            'message': 'Engine not found.'}), 404
    engine_version, models = get_latest_models(engine_id)

    if len(models) == 2:
        engine_config = ('[PAGE_PARSER]\n'
                         'RUN_LAYOUT_PARSER = yes\n'
                         'RUN_LINE_CROPPER = yes\n'
                         'RUN_OCR = yes\n'
                         'RUN_DECODER = no\n'
                         '\n\n')
    elif len(models) == 3:
        engine_config = ('[PAGE_PARSER]\n'
                         'RUN_LAYOUT_PARSER = yes\n'
                         'RUN_LINE_CROPPER = yes\n'
                         'RUN_OCR = yes\n'
                         'RUN_DECODER = yes\n'
                         '\n\n')
    else:
        if not engine:
            return jsonify({
                'status': 'failure',
                'message': 'Too many models for engine.'}), 500

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for model in models:
            for root, dirs, files in os.walk(os.path.join(app.config['MODELS_FOLDER'], model.name)):
                for file in files:
                    zf.write(os.path.join(root, file), os.path.join(model.name, file))
            engine_config += model.config + '\n\n'
        zf.writestr('config.ini', engine_config)
    memory_file.seek(0)

    return send_file(memory_file, attachment_filename='{}#{}.zip'.format(engine.name, engine_version.version), as_attachment=True)


@bp.route('/failed_processing/<string:page_id>', methods=['POST'])
@require_super_user_api_key
def report_failed_processing(page_id):
    notification_timestamp = get_notification()

    fail_type = str(request.headers.get('type'))
    traceback = str(request.data)
    engine_version_str = str(request.headers.get('engine_version'))

    engine = get_engine_by_page_id(page_id)
    engine_version = get_engine_version(engine.id, engine_version_str)

    change_page_to_failed(page_id, fail_type, traceback, engine_version.id)

    if fail_type == "PROCESSING_FAILED" and app.config['EMAIL_NOTIFICATION_ADDRESSES'] != []:
        print(datetime.datetime.now(), notification_timestamp, (datetime.datetime.now() - notification_timestamp).total_seconds(), app.config["MAX_EMAIL_FREQUENCY"])
        if (datetime.datetime.now() - notification_timestamp).total_seconds() > app.config["MAX_EMAIL_FREQUENCY"]:
            with app.app_context():
                mail = Mail()
                mail.init_app(app)

                page_db = get_page_by_id(page_id)
                request_db = get_request_by_page(page_db)
                api_key_db = get_api_key_by_id(request_db.api_key_id)

                message_body = "processing_client_hostname: {}\n" \
                               "processing_client_ip_address: {}\n" \
                               "owner_api_key: {}\n" \
                               "owner_description: {}\n" \
                               "engine_id: {}\n" \
                               "engine_name: {}\n" \
                               "request_id: {}\n" \
                               "page_id: {}\n" \
                               "page_name: {}\n" \
                               "page_url: {}\n" \
                               "####################\n" \
                               "traceback:\n{}" \
                               .format(request.headers.get('hostname'),
                                       request.headers.get('ip-address'),
                                       api_key_db.api_string,
                                       api_key_db.owner,
                                       engine.id,
                                       engine.name,
                                       request_db.id,
                                       page_db.id,
                                       page_db.name,
                                       page_db.url,
                                       traceback)

                msg = Message(subject="API Bot - PROCESSING_FAILED",
                              body=message_body,
                              sender=('PERO OCR - API BOT', app.config['MAIL_USERNAME']),
                              recipients=app.config['EMAIL_NOTIFICATION_ADDRESSES'])
                mail.send(msg)
            set_notification()

    return jsonify({
        'status': 'success'}), 200


@bp.route('/page_statistics', methods=['GET'])
@require_super_user_api_key
def page_statistics():
    state_stats, engine_stats = get_page_statistics()

    return jsonify({
        'status': 'success',
        'state_stats': state_stats,
        'engine_stats': engine_stats}), 200


@bp.route('/download_image/<string:request_id>/<string:page_name>', methods=['GET'])
@require_super_user_api_key
def download_image(request_id, page_name):
    extension = page_name.split('.')[-1]
    page_name = page_name[:-(len(extension)+1)]

    request_ = request_exists(request_id)
    if not request_:
        return jsonify({
            'status': 'failure',
            'message': 'Request doesn\'t exist.'}), 404
    page, page_state = get_page_and_page_state(request_id, page_name)
    if not page:
        return jsonify({
            'status': 'failure',
            'message': 'Page doesn\'t exist.'}), 404
    if page_state == PageState.CREATED:
        return jsonify({
            'status': 'failure',
            'message': 'Page isn\'t uploaded yet.'}), 202
    if page_state == PageState.PROCESSED:
        return jsonify({
            'status': 'failure',
            'message': 'Page is already processed.'}), 202

    return send_file(
        os.path.join(app.config['UPLOAD_IMAGES_FOLDER'], str(request_.id), '{}.{}'.format(page.name, extension))
    )


@bp.errorhandler(500)
def handle_exception(e):
    with app.app_context():
        mail = Mail()
        mail.init_app(app)
        msg = Message(subject="API Bot - INTERNAL SERVER ERROR",
                      body=traceback.format_exc(),
                      sender=('PERO OCR - API BOT', app.config['MAIL_USERNAME']),
                      recipients=app.config['EMAIL_NOTIFICATION_ADDRESSES'])
        mail.send(msg)

    abort(500)
