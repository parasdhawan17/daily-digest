"""Google identity verification and purpose-separated, signed browser sessions."""
import base64
import hashlib
import hmac
import json
import os
import time
from http.cookies import CookieError, SimpleCookie
from urllib.parse import urlparse

from stock_news.brevo import get_contact, _get_contact_attribute
from stock_news.config import BREVO_LIST_ID, BREVO_TICKERS_ATTRIBUTE, SITE_URL
from stock_news.relevance import parse_tickers

SESSION_COOKIE = 'tickr_session'
CSRF_COOKIE = 'tickr_csrf'
SESSION_SECONDS = 7 * 86400

class AuthError(ValueError):
    pass


def configured():
    return bool(os.getenv('GOOGLE_CLIENT_ID') and os.getenv('SESSION_SIGNING_SECRET'))


def cookies(handler):
    """Read only app cookies, independently of third-party cookie syntax.

    Google can set an unquoted JSON g_state cookie. SimpleCookie.load on the
    whole header stops at that value and silently drops subsequent cookies.
    Our tokens cannot contain semicolons, so parse each owned pair separately.
    """
    result = SimpleCookie()
    raw = getattr(handler, 'headers', {}).get('Cookie', '')
    for pair in raw.split(';'):
        name = pair.partition('=')[0].strip()
        if name not in (SESSION_COOKIE, CSRF_COOKIE):
            continue
        parsed = SimpleCookie()
        try:
            parsed.load(pair.strip())
        except CookieError:
            continue
        if name in parsed:
            result[name] = parsed[name].value
    return result


def cookie_header(name, value, max_age, *, http_only=True):
    secure = urlparse(os.getenv('SITE_URL') or SITE_URL).hostname not in ('localhost', '127.0.0.1')
    return f'{name}={value}; Path=/; Max-Age={max_age}; SameSite=Lax' + ('; HttpOnly' if http_only else '') + ('; Secure' if secure else '')


def sign_session(identity):
    secret = os.environ.get('SESSION_SIGNING_SECRET', '').strip()
    if not secret:
        raise AuthError('Browser sessions are not configured.')
    payload = {**identity, 'exp': int(time.time()) + SESSION_SECONDS, 'purpose': 'browser-session'}
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return body + '.' + signature


def get_session(handler):
    morsel = cookies(handler).get(SESSION_COOKIE)
    if not morsel:
        return None
    try:
        body, signature = morsel.value.split('.')
        secret = os.environ.get('SESSION_SIGNING_SECRET', '').strip()
        if not secret:
            raise ValueError()
        expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
        if payload['exp'] <= time.time() or payload['purpose'] != 'browser-session' or not payload['sub'] or not payload['email']:
            raise ValueError()
        return payload
    except (ValueError, KeyError, TypeError):
        raise AuthError('Your session expired. Please sign in again.')


def require_csrf(handler, payload=None):
    headers = getattr(handler, 'headers', {})
    expected_origin = (os.getenv('SITE_URL') or SITE_URL).rstrip('/')
    if headers.get('Origin') != expected_origin:
        raise AuthError('Invalid request origin.')
    cookie = cookies(handler).get(CSRF_COOKIE)
    supplied = headers.get('X-CSRF-Token', '') or (payload or {}).get('csrf_token', '')
    if not cookie or not supplied or not hmac.compare_digest(cookie.value, str(supplied)):
        raise AuthError('Invalid request token. Refresh and try again.')


def verify_google(credential):
    from google.auth.transport.requests import Request
    from google.oauth2.id_token import verify_oauth2_token
    try:
        claims = verify_oauth2_token(credential, Request(), os.environ['GOOGLE_CLIENT_ID'])
    except Exception as exc:
        raise AuthError('Could not verify Google sign-in. Please try again.') from exc
    email = str(claims.get('email', '')).strip().lower()
    if not claims.get('sub') or claims.get('email_verified') is not True:
        raise AuthError('Google must verify your email address first.')
    if not (email.endswith('@gmail.com') or claims.get('hd')):
        raise AuthError('Use email signup and confirmation for this email domain, or sign in with Gmail or Google Workspace.')
    return {'sub': claims['sub'], 'email': email}


def subscription(identity):
    api_key = os.environ.get('BREVO_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('Subscription lookup is not configured.')
    contact = get_contact(identity['email'], api_key)
    tickers = parse_tickers(_get_contact_attribute((contact or {}).get('attributes'), BREVO_TICKERS_ATTRIBUTE))
    active = bool(contact and not contact.get('emailBlacklisted') and int(BREVO_LIST_ID) in (contact.get('listIds') or []) and tickers)
    return {'ok': True, 'authenticated': True, 'email': identity['email'], 'tickers': tickers,
            'needs_subscription': not active, 'suppressed': bool(contact and contact.get('emailBlacklisted'))}
