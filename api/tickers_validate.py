"""Single-ticker validation handler."""

import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api._responses import read_json, send_json
from stock_news.finnhub import resolve_symbol_query


def handle_get(handler: BaseHTTPRequestHandler) -> None:
    query = parse_qs(urlparse(handler.path).query)
    symbol = (query.get("symbol") or [""])[0]
    validate_symbol(handler, symbol)


def handle_post(handler: BaseHTTPRequestHandler) -> None:
    try:
        payload = read_json(handler)
    except ValueError:
        send_json(handler, 400, {"ok": False, "valid": False, "error": "Invalid request body."})
        return
    symbol = str(payload.get("symbol") or "")
    validate_symbol(handler, symbol)


def validate_symbol(handler: BaseHTTPRequestHandler, symbol: str) -> None:
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        send_json(handler, 503, {"ok": False, "valid": False, "error": "Validation is not configured."})
        return

    ticker = symbol.strip().upper()
    if not ticker:
        send_json(handler, 400, {"ok": False, "valid": False, "error": "Enter a ticker or company name."})
        return

    try:
        match = resolve_symbol_query(symbol, api_key)
        if not match:
            send_json(
                handler,
                200,
                {
                    "ok": True,
                    "valid": False,
                    "error": f"Could not find a US listing for \"{symbol.strip()}\".",
                },
            )
            return
        send_json(handler, 200, {"ok": True, "valid": True, **match})
    except Exception:
        traceback.print_exc()
        send_json(handler, 503, {"ok": False, "valid": False, "error": "Could not validate right now."})


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        handle_get(self)

    def do_POST(self) -> None:
        handle_post(self)
