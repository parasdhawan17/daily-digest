"""Browser authentication endpoints."""
import os
import secrets
from api._responses import read_json, send_json
from stock_news.auth import (AuthError, configured, cookies, cookie_header, CSRF_COOKIE,
    SESSION_COOKIE, SESSION_SECONDS, get_session, require_csrf, sign_session, subscription, verify_google)


def handle_auth(handler, action):
    try:
        if action == 'config':
            existing = cookies(handler).get(CSRF_COOKIE)
            csrf = existing.value if existing and len(existing.value) == 43 else secrets.token_urlsafe(32)
            send_json(handler, 200, {'ok': True, 'enabled': configured(),
                'client_id': os.getenv('GOOGLE_CLIENT_ID', '') if configured() else '', 'csrf_token': csrf},
                headers={'Set-Cookie': cookie_header(CSRF_COOKIE, csrf, SESSION_SECONDS, http_only=False)})
            return
        if action == 'session':
            try:
                identity = get_session(handler)
            except AuthError:
                send_json(handler, 200, {'ok': True, 'authenticated': False},
                    headers={'Set-Cookie': cookie_header(SESSION_COOKIE, '', 0)})
                return
            send_json(handler, 200, subscription(identity) if identity else {'ok': True, 'authenticated': False})
            return
        payload = read_json(handler)
        require_csrf(handler, payload)
        if action == 'logout':
            send_json(handler, 200, {'ok': True}, headers={'Set-Cookie': cookie_header(SESSION_COOKIE, '', 0)})
            return
        if not configured():
            send_json(handler, 503, {'ok': False, 'error': 'Google sign-in is not configured.'})
            return
        identity = verify_google(str(payload.get('credential') or ''))
        state = subscription(identity)
        send_json(handler, 200, state, headers={'Set-Cookie': cookie_header(SESSION_COOKIE, sign_session(identity), SESSION_SECONDS)})
    except AuthError as exc:
        send_json(handler, 403, {'ok': False, 'error': str(exc)})
    except (ValueError, TypeError):
        send_json(handler, 400, {'ok': False, 'error': 'Invalid request.'})
    except Exception:
        send_json(handler, 503, {'ok': False, 'error': 'Sign-in service is unavailable. Please try again.'})
