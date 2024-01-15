from functools import wraps
from flask import request 
import os


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        print('request.headers: ', request.headers)

        token = None
        if 'x-api-key' in request.headers:
            token = request.headers['x-api-key']
        if not token:
            return {'message': "Token not found"}, 401
        if token != os.getenv('TOKEN'):
            return {'message': "Invalid token"}, 401

        return f(*args, **kwargs)

    return decorated
