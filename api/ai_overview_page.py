"""Public, shareable AI overview page for an Indian company."""

import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from stock_news.seo import company_metadata, snapshot_context

from api._responses import send_html
from stock_news.stock_detail import StockDataError, validate_request, get_page_snapshot

_env = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates"),
    autoescape=select_autoescape(["html"]),
)


def handle_page(handler):
    from api.index import request_path

    path = request_path(handler).rstrip("/")
    query = parse_qs(urlparse(handler.path).query)
    symbol = unquote(path.rsplit("/", 1)[-1]) if path.startswith("/ai-overview/") else (query.get("symbol") or [""])[0]
    try:
        symbol = validate_request(symbol)
    except StockDataError as error:
        send_html(handler, 404, _env.get_template("ai_overview.html").render(symbol="", error=str(error)))
        return
    try:
        snapshot = get_page_snapshot(symbol, os.environ.get('INDIANAPI_API_KEY', '').strip())
    except StockDataError as error:
        status = 404 if error.status == 404 else 503
        send_html(handler, status, _env.get_template('ai_overview.html').render(symbol='', error=str(error)))
        return
    send_html(handler, 200, _env.get_template('ai_overview.html').render(
        symbol=symbol, error='', seo=company_metadata(symbol, ai=True, name=snapshot['data']['name']),
        **snapshot_context(snapshot)))
