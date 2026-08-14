"""Ticker symbol search handler."""

import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api._responses import send_json
from stock_news.finnhub import search_symbols


def handle_get(handler: BaseHTTPRequestHandler) -> None:
    query = parse_qs(urlparse(handler.path).query)
    q = (query.get("q") or [""])[0]

    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        send_json(handler, 503, {"ok": False, "error": "Search is not configured."})
        return

    if len(q.strip()) < 1:
        send_json(handler, 400, {"ok": False, "error": "Enter a ticker or company name."})
        return

    try:
        results = search_symbols(q, api_key)
        send_json(handler, 200, {"ok": True, "results": results})
    except Exception:
        traceback.print_exc()
        send_json(handler, 503, {"ok": False, "error": "Could not search tickers right now."})


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        handle_get(self)
