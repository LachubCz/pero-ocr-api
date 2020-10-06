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
from app.db.model import PageState
from flask import current_app as app
from app.main.general import process_request, get_document_status, request_exists, cancel_request_by_id, \
                             get_engine_dict, get_page_by_id, check_save_path, get_page_by_preferred_engine, \
                             request_belongs_to_api_key, get_engine_version, get_engine_by_page_id, \
                             change_page_to_processed, get_page_and_page_state, get_engine, get_latest_models


@bp.route('/')
@bp.route('/docs')
@bp.route('/index')
def index():
    return redirect('https://app.swaggerhub.com/apis-docs/LachubCz/PERO-API/1.0.0#/')


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
            'status': 'failure'}
        )
    if not request_belongs_to_api_key(request.headers.get('api-key'), request_id):
        return jsonify({
            'status': 'failure'}
        )
    page, page_state = get_page_and_page_state(request_id, page_name)
    if not page:
        return jsonify({
            'status': 'failure'}
        )
    if page_state != PageState.PROCESSED:
        return jsonify({
            'status': 'failure'}
        )

    if format == 'alto':
        return send_file(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(request_.id), '{}_alto.xml'.format(page.name)),
                         attachment_filename='{}.xml' .format(page.name),
                         as_attachment=True)
    elif format == 'xml':
        return send_file(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(request_.id), '{}.xml'.format(page.name)),
                         attachment_filename='{}.xml'.format(page.name),
                         as_attachment=True)
    elif format == 'txt':
        return send_file(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(request_.id), '{}.txt'.format(page.name)),
                         attachment_filename='{}.txt'.format(page.name),
                         as_attachment=True)
    else:
        return jsonify({
            'status': 'failure'}
        )


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


@bp.route('/get_processing_request/<int:preferred_engine_id>', methods=['GET'])
@require_super_user_api_key
def get_processing_request(preferred_engine_id):
    page, engine_id = get_page_by_preferred_engine(preferred_engine_id)

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

    file = request.files['alto']
    file.save(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(page.request_id),
                           secure_filename(page.name + '_alto.xml')))
    file = request.files['xml']
    file.save(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(page.request_id),
                           secure_filename(page.name + '.xml')))
    file = request.files['txt']
    file.save(os.path.join(app.config['PROCESSED_REQUESTS_FOLDER'], str(page.request_id),
                           secure_filename(page.name + '.txt')))

    return jsonify({
        'status': 'success'}
    )


@bp.route('/download_engine/<int:engine_id>', methods=['GET'])
@require_super_user_api_key
def download_engine(engine_id):
    engine = get_engine(engine_id)
    if not engine:
        return jsonify({
            'status': 'failure'}
        )
    engine_version, models = get_latest_models(engine_id)

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for model in models:
            for root, dirs, files in os.walk(model.path):
                for file in files:
                    zf.write(os.path.join(root, file), os.path.join(model.name, file))
        zf.write(engine_version.config_path, 'config.ini')
    memory_file.seek(0)

    return send_file(memory_file, attachment_filename='{}#{}.zip'.format(engine.name, engine_version.version), as_attachment=True)
