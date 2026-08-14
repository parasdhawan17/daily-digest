"""Vercel serverless handler for ticker symbol search."""

import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stock_news.finnhub import search_symbols


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        q = (query.get("q") or [""])[0]

        api_key = os.environ.get("FINNHUB_API_KEY")
        if not api_key:
            self._json(503, {"ok": False, "error": "Search is not configured."})
            return

        if len(q.strip()) < 1:
            self._json(400, {"ok": False, "error": "Enter a ticker or company name."})
            return

        try:
            results = search_symbols(q, api_key)
            self._json(200, {"ok": True, "results": results})
        except Exception:
            traceback.print_exc()
            self._json(503, {"ok": False, "error": "Could not search tickers right now."})

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
