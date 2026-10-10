"""Public daily homepage signal endpoint."""
import os
from api._responses import send_json
from stock_news.home_ai_signal import get_home_ai_signal


def handle_get(handler):
    payload, ttl = get_home_ai_signal(os.environ.get('INDIANAPI_API_KEY', '').strip())
    status = 200 if payload.get('ok') or payload.get('code') == 'no_match' else 503
    send_json(handler, status, payload, headers={
        'Cache-Control': f'public, max-age=0, s-maxage={ttl}' if ttl else 'no-store'
    })
