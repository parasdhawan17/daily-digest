"""Public stock pages and section data."""
import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from api._responses import send_json, send_html
from stock_news.stock_detail import StockDataError, get_data, validate_request

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
                                get('series', 'quarter_results'), os.environ.get('INDIANAPI_API_KEY', '').strip())
        send_json(handler, 200, payload, headers={'Cache-Control': f'public, max-age=0, s-maxage={ttl}'})
    except StockDataError as error:
        send_json(handler, error.status, {'ok': False, 'code': error.code, 'error': str(error)})
