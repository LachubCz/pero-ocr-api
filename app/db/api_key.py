import base64
import random
import hashlib
from functools import wraps
from flask import request, abort

from app.db import ApiKey
from app.db import Permission


def generate_hash_key():
    """
    @return: A hashkey for use to authenticate agains the API.
    """
    return base64.b64encode(hashlib.sha256(str(random.getrandbits(256)).encode('utf-8')).digest(),
                            random.choice(['rA', 'aZ', 'gQ', 'hH', 'hG', 'aR', 'DD']).encode('utf-8')).decode('utf-8').rstrip('==')


def get_apiauth_object_by_key_u(key):
    """
    Query the datastorage for an API key.
    @return: apiauth sqlachemy object.
    """
    api_string = ApiKey.query.filter(ApiKey.api_string == key).first()
    return api_string


def get_apiauth_object_by_key_su(key):
    """
    Query the datastorage for an API key.
    @return: apiauth sqlachemy object.
    """
    api_string = ApiKey.query.filter(ApiKey.api_string == key).filter(ApiKey.permission == Permission.SUPER_USER).first()
    return api_string


def match_api_keys(key, permission):
    """
    Match API keys
    @param key: API key from request
    @return: boolean
    """
    if key is None:
        return False

    if permission == Permission.USER:
        api_key = get_apiauth_object_by_key_u(key)
    elif permission == Permission.SUPER_USER:
        api_key = get_apiauth_object_by_key_su(key)

    if api_key is not None:
        return True
    return False


def require_super_user_api_key(f):
    """
    @param f: flask function
    @return: decorator, return the wrapped function or abort json object.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if match_api_keys(request.headers.get('api-key'), Permission.SUPER_USER):
            return f(*args, **kwargs)
        else:
            # todo send string bad api key
            abort(401)
    return decorated


def require_user_api_key(f):
    """
    @param f: flask function
    @return: decorator, return the wrapped function or abort json object.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if match_api_keys(request.headers.get('api-key'), Permission.USER):
            return f(*args, **kwargs)
        else:
            abort(401)
    return decorated
