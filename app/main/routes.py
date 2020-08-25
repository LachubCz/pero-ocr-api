import json
from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from app.main import bp


@bp.route('/')
@bp.route('/docs')
@bp.route('/index')
def index():
    return render_template('documentation.html')


@bp.route('/post_processing_request', methods=['POST'])
def post_processing_request():
    file = request.files['data']
    content = file.read()
    json_string = json.loads(content)
    print(json_string)

    return jsonify({
        'status': 'success',
        'request_id': '1'}
    )


@bp.route('/request_status', methods=['GET'])
def request_status():
    return jsonify({
        'status': 'success',
        'request_status': 'NEW'}
    )


@bp.route('/ocr_systems', methods=['GET'])
def ocr_systems():
    return jsonify({
        'status': 'success',
        'ocr_system': []}
    )


@bp.route('/download_results', methods=['GET'])
def download_results():
    return send_file('filepath', as_attachment=True, attachment_filename='filename')


@bp.route('/cancel_request/<string:request_id>', methods=['POST'])
def cancel_request(request_id):
    return jsonify({
        'status': 'success'}
    )


@bp.route('/get_processing_request', methods=['GET'])
def get_processing_request():
    file = request.files['data']
    content = file.read()
    changes = json.loads(content)
    print(changes)
    return render_template('documentation.html')


@bp.route('/upload_results', methods=['POST'])
def upload_results():
    file = request.files['data']
    content = file.read()
    changes = json.loads(content)
    print(changes)
    return render_template('documentation.html')
