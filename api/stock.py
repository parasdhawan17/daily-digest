"""Public stock pages and section data."""
import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from api._responses import read_json, send_json, send_html
from stock_news.stock_detail import StockDataError, get_data, validate_request
from stock_news.stock_ai_overview import get_stock_ai_overview
from stock_news.stock_section_ai import get_stock_section_explanation

_env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parent.parent / 'templates'),
                   autoescape=select_autoescape(['html']))


def handle_page(handler):
    from api.index import request_path
    query = parse_qs(urlparse(handler.path).query)
    path = request_path(handler).rstrip('/')
    symbol = unquote(path.rsplit('/', 1)[-1]) if path.startswith('/stocks/') else (query.get('symbol') or [''])[0]
    try:
        symbol = validate_request(symbol)
    except StockDataError as error:
        send_html(handler, 404, _env.get_template('stock.html').render(symbol='', error=str(error)))
        return
    send_html(handler, 200, _env.get_template('stock.html').render(symbol=symbol, error=''))


def handle_data(handler):
    query = parse_qs(urlparse(handler.path).query)
    get = lambda key, default: (query.get(key) or [default])[0]
    try:
        payload, ttl = get_data(get('symbol', ''), get('section', 'core'), get('period', '1yr'),
                                get('series', 'quarter_results'), os.environ.get('INDIANAPI_API_KEY', '').strip(),
                                history_filter=get('filter', 'price'))
        send_json(handler, 200, payload, headers={'Cache-Control': f'public, max-age=0, s-maxage={ttl}'})
    except StockDataError as error:
        send_json(handler, error.status, {'ok': False, 'code': error.code, 'error': str(error)})


def handle_ai(handler):
    query = parse_qs(urlparse(handler.path).query)
    symbol = (query.get('symbol') or [''])[0]
    try:
        symbol = validate_request(symbol)
        core_payload, _ = get_data(symbol, 'core', '1yr', 'quarter_results',
                                   os.environ.get('INDIANAPI_API_KEY', '').strip())
        payload, ttl = get_stock_ai_overview(symbol, core_payload['data'])
        if not payload:
            send_json(handler, 503, {'ok': False, 'code': 'ai_unavailable',
                                     'error': 'The AI overview is temporarily unavailable.'})
            return
        send_json(handler, 200, payload, headers={
            'Cache-Control': f'public, max-age=0, s-maxage={ttl}, stale-while-revalidate=3600'
        })
    except StockDataError as error:
        send_json(handler, error.status, {'ok': False, 'code': error.code, 'error': str(error)})
    except Exception:
        send_json(handler, 503, {'ok': False, 'code': 'ai_unavailable',
                                 'error': 'The AI overview is temporarily unavailable.'})


def handle_section_ai(handler):
    try:
        if int(handler.headers.get('Content-Length') or 0) > 12000:
            send_json(handler, 413, {'ok': False, 'code': 'request_too_large',
                                     'error': 'The selected section is too large to summarize.'})
            return
        body = read_json(handler)
    except (ValueError, TypeError):
        send_json(handler, 400, {'ok': False, 'code': 'invalid_request',
                                 'error': 'The section summary request is invalid.'})
        return
    try:
        symbol = validate_request(body.get('symbol', ''))
        payload, _ = get_stock_section_explanation(
            symbol, body.get('section'), body.get('card_id'), body.get('title'), body.get('text'))
        if not payload:
            send_json(handler, 503, {'ok': False, 'code': 'ai_unavailable',
                                     'error': 'The AI section explainer is temporarily unavailable.'})
            return
        send_json(handler, 200, payload)
    except ValueError as error:
        send_json(handler, 400, {'ok': False, 'code': 'invalid_section', 'error': str(error)})
    except StockDataError as error:
        send_json(handler, error.status, {'ok': False, 'code': error.code, 'error': str(error)})
    except Exception:
        send_json(handler, 503, {'ok': False, 'code': 'ai_unavailable',
                                 'error': 'The AI section explainer is temporarily unavailable.'})
