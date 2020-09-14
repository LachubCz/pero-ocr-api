import json
from flask import render_template, redirect, url_for, flash, request, jsonify, send_file, abort
from app.main import bp
from app.db.api_key import require_user_api_key, require_super_user_api_key

from app.main.general import process_request, get_document_status, request_exists, cancel_request_by_id, get_ocr_systems


@bp.route('/')
@bp.route('/docs')
@bp.route('/index')
def index():
    return render_template('documentation.html')


@bp.route('/post_processing_request', methods=['POST'])
@require_user_api_key
def post_processing_request():
    file = request.files['data']
    content = file.read()
    json_content = json.loads(content)
    db_request = process_request(json_content)

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
        abort(404)

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


@bp.route('/download_results', methods=['GET'])
@require_user_api_key
def download_results():
    return send_file('filepath', as_attachment=True, attachment_filename='filename')


@bp.route('/cancel_request/<string:request_id>', methods=['POST'])
@require_user_api_key
def cancel_request(request_id):
    if not request_exists(request_id):
        abort(404)
    cancel_request_by_id(request_id)
    return jsonify({
        'status': 'success'}
    )


@bp.route('/get_processing_request', methods=['GET'])
@require_super_user_api_key
def get_processing_request():
    request = None  # database query
    return jsonify({
        'request_id': request.id, 'baseline_id': request.baseline_id, 'ocr_id': request.ocr_id,
        'language_model_id': request.language_model_id, 'document': {'id': request.document.id, 'images': []}}
    )


@bp.route('/upload_results', methods=['POST'])
@require_super_user_api_key
def upload_results():
    file = request.files['data']
    content = file.read()

    return jsonify({
        'status': 'success'}
    )
