import os

API_KEY = os.environ.get('API_KEY', 'secret-token')


def authenticate(req):
    """Simple authentication node: expects header X-API-KEY or JSON api_key"""
    headers = getattr(req, 'headers', {}) or {}
    body = getattr(req, 'json', None) or {}
    body_key = body.get('api_key') if isinstance(body, dict) else None
    key = headers.get('X-API-KEY') or body_key
    meta = {'method_checked': 'header/json', 'expected_api_key': API_KEY}
    if key == API_KEY:
        return True, meta
    return False, {'error': 'invalid_api_key'}
