import os
import os.path
import zipfile
from io import BytesIO
from urllib.parse import urlparse
from flask import redirect, request, jsonify, send_file
from werkzeug.utils import secure_filename
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
                             get_document_pages, change_page_to_failed, get_page_statistics, change_page_path


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
        path = '{}://{}/download_image/{}/{}'.format(o.scheme, o.netloc, request_id, page_name+'.'+file.filename.split('.')[-1])
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
    if page_state != PageState.PROCESSED:
        return jsonify({
            'status': 'failure',
            'message': 'Page isn\'t processed.'}), 202

    if format == 'alto':
        return send_file(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(request_.id), '{}_alto.xml'.format(page.name)),
                         attachment_filename='{}.xml' .format(page.name),
                         as_attachment=True)
    elif format == 'page':
        return send_file(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(request_.id), '{}_page.xml'.format(page.name)),
                         attachment_filename='{}.xml'.format(page.name),
                         as_attachment=True)
    elif format == 'txt':
        return send_file(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(request_.id), '{}.txt'.format(page.name)),
                         attachment_filename='{}.txt'.format(page.name),
                         as_attachment=True)
    else:
        return jsonify({
            'status': 'failure',
            'message': 'Bad export format.'}), 400


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

    file = request.files['alto']
    file.save(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(page.request_id),
                           secure_filename(page.name + '_alto.xml')))
    file = request.files['page']
    file.save(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(page.request_id),
                           secure_filename(page.name + '_page.xml')))
    file = request.files['txt']
    file.save(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(page.request_id),
                           secure_filename(page.name + '.txt')))

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
    fail_type = str(request.headers.get('type'))
    traceback = str(request.data)
    engine_version_str = str(request.headers.get('engine_version'))

    engine = get_engine_by_page_id(page_id)
    engine_version = get_engine_version(engine.id, engine_version_str)

    change_page_to_failed(page_id, fail_type, traceback, engine_version.id)

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
