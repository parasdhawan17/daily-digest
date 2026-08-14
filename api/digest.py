"""Digest page handler."""

import os
import sys
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api._responses import send_html
from stock_news.digest import collect_digest_data, filter_sections
from stock_news.formatting import format_fetched_at_label
from stock_news.render import build_digest_error, build_web_digest
from stock_news.tokens import TokenError, verify_digest_token


def handle_get(handler: BaseHTTPRequestHandler) -> None:
    query = parse_qs(urlparse(handler.path).query)
    token = (query.get("t") or [None])[0]

    if not token:
        html = build_digest_error(
            "Missing link",
            "Open the digest link from your email, or subscribe to get personalized digests.",
        )
        send_html(handler, 400, html)
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
        send_html(handler, status, html)
        return

    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        html = build_digest_error(
            "Service unavailable",
            "The digest service is not configured.",
            detail="FINNHUB_API_KEY is missing.",
        )
        send_html(handler, 503, html)
        return

    try:
        sections, _ = collect_digest_data(tickers, api_key)
        sections = filter_sections(sections, tickers)
        fetched_at = format_fetched_at_label(datetime.now().astimezone())
        html = build_web_digest(sections, tickers, fetched_at_label=fetched_at)
        send_html(handler, 200, html)
    except Exception:
        traceback.print_exc()
        html = build_digest_error(
            "Something went wrong",
            "We couldn't load your digest right now.",
            detail="Please try again in a few minutes.",
        )
        send_html(handler, 503, html)


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        handle_get(self)
