"""Vercel serverless handler for /digest (rewritten from /api/digest)."""

import os
import sys
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Vercel runs api/ from project root; ensure imports resolve.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stock_news.digest import collect_digest_data, filter_sections
from stock_news.formatting import format_fetched_at_label
from stock_news.render import build_digest_error, build_web_digest
from stock_news.tokens import TokenError, verify_digest_token


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        token = (query.get("t") or [None])[0]

        if not token:
            html = build_digest_error(
                "Missing link",
                "Open the digest link from your email, or subscribe to get personalized digests.",
            )
            self._respond(400, html)
            return

        try:
            tickers = verify_digest_token(token)
        except TokenError as exc:
            message = str(exc)
            if "expired" in message.lower():
                title = "Link expired"
                detail = "Open the latest email and use the link there."
            elif "signature" in message.lower() or "format" in message.lower():
                title = "Invalid link"
                detail = "This digest link is not valid."
            else:
                title = "Invalid link"
                detail = message
            html = build_digest_error(title, "We couldn't open this digest.", detail=detail)
            status = 403 if "expired" in message.lower() or "signature" in message.lower() else 400
            self._respond(status, html)
            return

        api_key = os.environ.get("FINNHUB_API_KEY")
        if not api_key:
            html = build_digest_error(
                "Service unavailable",
                "The digest service is not configured.",
                detail="FINNHUB_API_KEY is missing.",
            )
            self._respond(503, html)
            return

        try:
            sections, _ = collect_digest_data(tickers, api_key)
            sections = filter_sections(sections, tickers)
            fetched_at = format_fetched_at_label(datetime.now().astimezone())
            html = build_web_digest(sections, tickers, fetched_at_label=fetched_at)
            self._respond(200, html)
        except Exception:
            traceback.print_exc()
            html = build_digest_error(
                "Something went wrong",
                "We couldn't load your digest right now.",
                detail="Please try again in a few minutes.",
            )
            self._respond(503, html)

    def _respond(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
