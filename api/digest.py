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
from stock_news.ai_summary import generate_ai_summary
from stock_news.digest import collect_digest_data, filter_sections
from stock_news.formatting import format_fetched_at_label
from stock_news.markets import market_of
from stock_news.render import build_digest_error, build_web_digest
from stock_news.tokens import TokenError, verify_digest_token


def _missing_data_keys(tickers: list[str]) -> list[str]:
    missing: list[str] = []
    needs_us = any(market_of(ticker) == "US" for ticker in tickers)
    needs_in = any(market_of(ticker) == "IN" for ticker in tickers)
    if needs_us and not os.environ.get("FINNHUB_API_KEY", "").strip():
        missing.append("FINNHUB_API_KEY")
    if needs_in and not os.environ.get("INDIANAPI_API_KEY", "").strip():
        missing.append("INDIANAPI_API_KEY")
    return missing


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

    missing = _missing_data_keys(tickers)
    if missing:
        html = build_digest_error(
            "Service unavailable",
            "The digest service is not configured.",
            detail="Missing: " + ", ".join(missing),
        )
        send_html(handler, 503, html)
        return

    finnhub_key = os.environ.get("FINNHUB_API_KEY", "").strip()
    indianapi_key = os.environ.get("INDIANAPI_API_KEY", "").strip()

    try:
        sections, _ = collect_digest_data(
            tickers,
            finnhub_key=finnhub_key,
            indianapi_key=indianapi_key,
        )
        sections = filter_sections(sections, tickers)
        ai_summary = generate_ai_summary(sections)
        fetched_at = format_fetched_at_label(datetime.now().astimezone())
        html = build_web_digest(
            sections,
            tickers,
            fetched_at_label=fetched_at,
            ai_summary=ai_summary,
        )
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
