"""Unified Vercel Python entrypoint — routes all API paths to handler modules."""

import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.digest import handler as DigestHandler
from api.subscribe import handler as SubscribeHandler
from api.tickers_search import handler as SearchHandler
from api.tickers_validate import handler as ValidateHandler


def _route(path: str) -> str | None:
    normalized = path.rstrip("/") or "/"
    if normalized in ("/digest", "/api/digest", "/api/index"):
        return "digest"
    if normalized == "/api/subscribe":
        return "subscribe"
    if normalized in ("/api/tickers/search", "/api/tickers_search"):
        return "search"
    if normalized in ("/api/tickers/validate", "/api/tickers_validate"):
        return "validate"
    return None


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        route = _route(urlparse(self.path).path)
        if route == "digest":
            DigestHandler.do_GET(self)
        elif route == "search":
            SearchHandler.do_GET(self)
        elif route == "validate":
            ValidateHandler.do_GET(self)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        route = _route(urlparse(self.path).path)
        if route == "subscribe":
            SubscribeHandler.do_POST(self)
        elif route == "validate":
            ValidateHandler.do_POST(self)
        else:
            self.send_error(404)
