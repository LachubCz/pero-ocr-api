import base64
import random
import hashlib
from functools import wraps
from flask import request, abort

from app.db import ApiKey


def generate_hash_key():
    """
    @return: A hashkey for use to authenticate agains the API.
    """
    return base64.b64encode(hashlib.sha256(str(random.getrandbits(256)).encode('utf-8')).digest(),
                            random.choice(['rA', 'aZ', 'gQ', 'hH', 'hG', 'aR', 'DD']).encode('utf-8')).decode('utf-8').rstrip('==')


def get_apiauth_object_by_key(key):
    """
    Query the datastorage for an API key.
    @return: apiauth sqlachemy object.
    """
    api_string = ApiKey.query.filter(ApiKey.api_string == key).first()
    return api_string


def match_api_keys(key):
    """
    Match API keys
    @param key: API key from request
    @return: boolean
    """
    if key is None:
        return False
    api_key = get_apiauth_object_by_key(key)
    if api_key is not None:
        return True
    return False


def require_app_key(f):
    """
    @param f: flask function
    @return: decorator, return the wrapped function or abort json object.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if match_api_keys(request.headers.get('api-key')):
            return f(*args, **kwargs)
        else:
            abort(401)
    return decorated
