"""Vercel serverless handler for single-ticker validation."""

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

from stock_news.finnhub import resolve_symbol_query


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        symbol = (query.get("symbol") or [""])[0]
        self._validate(symbol)

    def do_POST(self):
        try:
            payload = self._read_json()
        except ValueError:
            self._json(400, {"ok": False, "valid": False, "error": "Invalid request body."})
            return
        symbol = str(payload.get("symbol") or "")
        self._validate(symbol)

    def _validate(self, symbol: str) -> None:
        api_key = os.environ.get("FINNHUB_API_KEY")
        if not api_key:
            self._json(503, {"ok": False, "valid": False, "error": "Validation is not configured."})
            return

        ticker = symbol.strip().upper()
        if not ticker:
            self._json(400, {"ok": False, "valid": False, "error": "Enter a ticker or company name."})
            return

        try:
            match = resolve_symbol_query(symbol, api_key)
            if not match:
                self._json(
                    200,
                    {
                        "ok": True,
                        "valid": False,
                        "error": f"Could not find a US listing for \"{symbol.strip()}\".",
                    },
                )
                return
            self._json(200, {"ok": True, "valid": True, **match})
        except Exception:
            traceback.print_exc()
            self._json(503, {"ok": False, "valid": False, "error": "Could not validate right now."})

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("expected object")
        return data

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
