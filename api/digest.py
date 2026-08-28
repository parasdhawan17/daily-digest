"""Digest page handler."""

import os
import sys
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api._responses import read_json, send_html, send_json
from stock_news.ai_summary import generate_ai_summary
from stock_news.digest import collect_digest_data, filter_sections
from stock_news.formatting import format_fetched_at_label
from stock_news.markets import market_of
from stock_news.render import build_digest_error, build_web_digest, build_web_section
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


def _verify_token(handler: BaseHTTPRequestHandler) -> tuple[str | None, list[str] | None]:
    query = parse_qs(urlparse(handler.path).query)
    token = (query.get("t") or [None])[0]
    if not token:
        return None, None
    try:
        return token, verify_digest_token(token)
    except TokenError:
        return token, None


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

    # The page shell is intentionally rendered before any provider or AI call.
    fetched_at_instant = datetime.now(timezone.utc)
    fetched_at = format_fetched_at_label(fetched_at_instant)
    html = build_web_digest(
        [],
        tickers,
        fetched_at_label=fetched_at,
        fetched_at_iso=fetched_at_instant.isoformat(),
        progressive=True,
        progressive_token=token,
    )
    send_html(handler, 200, html)


def handle_data_get(handler: BaseHTTPRequestHandler) -> None:
    """Return one ticker's data so the browser can progressively render it."""
    token, tickers = _verify_token(handler)
    query = parse_qs(urlparse(handler.path).query)
    ticker = (query.get("ticker") or [""])[0].strip().upper()
    if not token or not tickers:
        send_json(handler, 403, {"ok": False, "error": "Invalid digest link."})
        return
    if ticker not in tickers:
        send_json(handler, 400, {"ok": False, "error": "Ticker is not in this digest."})
        return

    missing = _missing_data_keys([ticker])
    if missing:
        send_json(handler, 503, {"ok": False, "error": "Missing: " + ", ".join(missing)})
        return

    try:
        sections, _ = collect_digest_data(
            [ticker],
            finnhub_key=os.environ.get("FINNHUB_API_KEY", "").strip(),
            indianapi_key=os.environ.get("INDIANAPI_API_KEY", "").strip(),
            include_earnings=True,
            include_price_ranges=True,
            include_indian_media=True,
        )
        section = filter_sections(sections, [ticker])[0]
        send_json(handler, 200, {"ok": True, "section": section, "html": build_web_section(section)})
    except Exception:
        traceback.print_exc()
        send_json(handler, 503, {"ok": False, "error": "Could not load this ticker right now."})


def handle_ai_post(handler: BaseHTTPRequestHandler) -> None:
    """Generate the optional AI briefing after the visible sections are loaded."""
    _token, tickers = _verify_token(handler)
    if not tickers:
        send_json(handler, 403, {"ok": False, "error": "Invalid digest link."})
        return
    try:
        payload = read_json(handler)
        sections = payload.get("sections")
        if not isinstance(sections, list):
            raise ValueError("sections must be a list")
        allowed = set(tickers)
        safe_sections = [item for item in sections if isinstance(item, dict) and item.get("ticker") in allowed]
        send_json(handler, 200, {"ok": True, "ai_summary": generate_ai_summary(safe_sections)})
    except Exception:
        traceback.print_exc()
        send_json(handler, 200, {"ok": True, "ai_summary": None})


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        handle_get(self)
