import os
import time
import ntpath
import zipfile
from io import BytesIO
import glob
import json
from flask import render_template, redirect, url_for, flash, request, jsonify, send_file, abort
from werkzeug.utils import secure_filename
from app.main import bp
from app.db.api_key import require_user_api_key, require_super_user_api_key
from app.wsgi import app
from app.main.general import process_request, get_document_status, request_exists, cancel_request_by_id, \
                             get_ocr_systems, get_page_by_id, check_save_path, get_page_by_preferred_engine, \
                             request_belongs_to_api_key, get_engine_version, get_engine_by_page_id, \
                             change_page_to_processed, is_request_processed


@bp.route('/')
@bp.route('/docs')
@bp.route('/index')
def index():
    return render_template('documentation.html')


@bp.route('/post_processing_request', methods=['POST'])
@require_user_api_key
def post_processing_request():
    api_string = request.headers.get('api-key')
    file = request.files['data']
    content = file.read()
    json_content = json.loads(content)
    db_request = process_request(api_string, json_content)

    if db_request is not None:
        return jsonify({
            'status': 'success',
            'request_id': db_request.id}
        )
    else:
        return jsonify({
            'status': 'failure',
            'request_id': None}
        )


@bp.route('/request_status/<string:request_id>', methods=['GET'])
@require_user_api_key
def request_status(request_id):
    if not request_exists(request_id):
        return jsonify({
            'status': 'failure',
            'request_status': None,
            'quality': None}
        )

    if not request_belongs_to_api_key(request.headers.get('api-key'), request_id):
        return jsonify({
            'status': 'failure',
            'request_status': None,
            'quality': None}
        )

    status, quality = get_document_status(request_id)

    return jsonify({
        'status': 'success',
        'request_status': '{} %' .format(status),
        'quality': '{} %' .format(quality)}
    )


@bp.route('/ocr_systems', methods=['GET'])
@require_user_api_key
def ocr_systems():
    ocr_systems = get_ocr_systems()
    return jsonify({
        'status': 'success',
        'ocr_system': ocr_systems}
    )


@bp.route('/download_results/<string:request_id>', methods=['GET'])
@require_user_api_key
def download_results(request_id):
    request_ = request_exists(request_id)
    if not request_:
        return jsonify({
            'status': 'failure'}
        )
    if not request_belongs_to_api_key(request.headers.get('api-key'), request_id):
        return jsonify({
            'status': 'failure'}
        )
    if not is_request_processed(request_id):
        return jsonify({
            'status': 'failure'}
        )

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        files = glob.glob(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(request_.id)) + '/*.xml')
        for filename in files:
            f = open(filename, "r")
            content = f.read()
            page = zipfile.ZipInfo(ntpath.basename(filename))
            page.date_time = time.localtime(time.time())[:6]
            page.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(page, content)
    memory_file.seek(0)

    return send_file(memory_file, attachment_filename='pages.zip', as_attachment=True)


@bp.route('/cancel_request/<string:request_id>', methods=['POST'])
@require_user_api_key
def cancel_request(request_id):
    if not request_exists(request_id):
        return jsonify({
            'status': 'failure'}
        )

    if not request_belongs_to_api_key(request.headers.get('api-key'), request_id):
        return jsonify({
            'status': 'failure'}
        )

    cancel_request_by_id(request_id)
    return jsonify({
        'status': 'success'}
    )


@bp.route('/get_processing_request/<int:preferred_engine>', methods=['GET'])
@require_super_user_api_key
def get_processing_request(preferred_engine):
    page, engine_id = get_page_by_preferred_engine(preferred_engine)

    if page:
        return jsonify({
            'status': 'success',
            'page_id': page.id,
            'page_url': page.url,
            'engine_id': engine_id}
        )
    else:
        return jsonify({
            'status': 'failure',
            'page_id': None,
            'page_url': None,
            'engine_id': None}
        )


@bp.route('/upload_results/<string:page_id>', methods=['POST'])
@require_super_user_api_key
def upload_results(page_id):
    page = get_page_by_id(page_id)
    if not page:
        return jsonify({
            'status': 'failure'}
        )

    score = int(request.headers.get('score'))
    engine_version_str = str(request.headers.get('engine-version'))

    engine = get_engine_by_page_id(page_id)
    engine_version = get_engine_version(engine.id, engine_version_str)

    change_page_to_processed(page_id, score, engine_version.id)
    check_save_path(page.request_id)

    file = request.files['data']
    file.save(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(page.request_id), secure_filename(page.name + '.xml')))

    return jsonify({
        'status': 'success'}
    )
