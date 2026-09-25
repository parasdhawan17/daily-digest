"""Public, shareable AI overview page for an Indian company."""

from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from api._responses import send_html
from stock_news.stock_detail import StockDataError, validate_request

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
    send_html(handler, 200, _env.get_template("ai_overview.html").render(symbol=symbol, error=""))
