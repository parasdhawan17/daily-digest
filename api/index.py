"""Unified Vercel Python entrypoint — routes all API paths to handler modules."""

import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.digest import handle_ai_post, handle_data_get, handle_get as handle_digest
from api.subscribe import handle_post as handle_subscribe
from api.tickers_search import handle_get as handle_search
from api.tickers_validate import handle_get as handle_validate_get, handle_post as handle_validate_post

_ORIGINAL_PATH_HEADERS = (
    "x-vercel-original-url",
    "x-forwarded-uri",
    "x-original-url",
    "x-invoke-path",
)


def request_path(handler: BaseHTTPRequestHandler) -> str:
    for header in _ORIGINAL_PATH_HEADERS:
        value = handler.headers.get(header)
        if value:
            return urlparse(value).path
    return urlparse(handler.path).path


def route(handler: BaseHTTPRequestHandler) -> str | None:
    query = parse_qs(urlparse(handler.path).query)
    explicit = (query.get("route") or [""])[0].strip().lower()
    if explicit in ("digest", "digest-data", "digest-ai", "subscribe", "search", "validate"):
        return explicit

    normalized = request_path(handler).rstrip("/") or "/"
    if normalized in ("/digest", "/api/digest", "/api/index"):
        return "digest"
    if normalized == "/api/digest-data":
        return "digest-data"
    if normalized == "/api/digest-ai":
        return "digest-ai"
    if normalized == "/api/subscribe":
        return "subscribe"
    if normalized in ("/api/tickers/search", "/api/tickers_search"):
        return "search"
    if normalized in ("/api/tickers/validate", "/api/tickers_validate"):
        return "validate"
    return None


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        matched = route(self)
        if matched == "digest":
            handle_digest(self)
        elif matched == "digest-data":
            handle_data_get(self)
        elif matched == "search":
            handle_search(self)
        elif matched == "validate":
            handle_validate_get(self)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        matched = route(self)
        if matched == "subscribe":
            handle_subscribe(self)
        elif matched == "digest-ai":
            handle_ai_post(self)
        elif matched == "validate":
            handle_validate_post(self)
        else:
            self.send_error(404)
