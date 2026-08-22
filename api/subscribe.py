"""Subscribe / update tickers handler."""

import os
import re
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api._responses import read_json, send_json
from stock_news.brevo import BrevoError, subscribe_or_update
from stock_news.config import (
    BREVO_DOI_TEMPLATE_ID,
    BREVO_LIST_ID,
    BREVO_TICKERS_ATTRIBUTE,
    MAX_TICKERS_PER_USER,
    SITE_URL,
)
from stock_news.market_data import validate_symbol
from stock_news.markets import market_of
from stock_news.relevance import parse_tickers

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def handle_post(handler: BaseHTTPRequestHandler) -> None:
    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    list_id = BREVO_LIST_ID
    template_id = os.environ.get("BREVO_DOI_TEMPLATE_ID", "").strip()
    finnhub_key = os.environ.get("FINNHUB_API_KEY", "").strip()
    indianapi_key = os.environ.get("INDIANAPI_API_KEY", "").strip()

    if not api_key or not template_id:
        missing = [
            name
            for name, value in (
                ("BREVO_API_KEY", api_key),
                ("BREVO_DOI_TEMPLATE_ID", template_id),
            )
            if not value
        ]
        send_json(
            handler,
            503,
            {
                "ok": False,
                "error": "Subscribe is not configured. Missing: " + ", ".join(missing),
            },
        )
        return
    if not finnhub_key and not indianapi_key:
        send_json(handler, 503, {"ok": False, "error": "Ticker validation is not configured."})
        return

    try:
        payload = read_json(handler)
    except ValueError:
        send_json(handler, 400, {"ok": False, "error": "Invalid request body."})
        return

    email = str(payload.get("email") or "").strip().lower()
    if not email or not EMAIL_PATTERN.match(email):
        send_json(handler, 400, {"ok": False, "error": "Enter a valid email address."})
        return

    raw_tickers = payload.get("tickers")
    if not isinstance(raw_tickers, list):
        send_json(handler, 400, {"ok": False, "error": "Select at least one ticker."})
        return

    tickers = parse_tickers([str(item) for item in raw_tickers])
    if not tickers:
        send_json(handler, 400, {"ok": False, "error": "Select at least one valid ticker."})
        return
    if len(tickers) > MAX_TICKERS_PER_USER:
        send_json(handler, 400, {"ok": False, "error": f"Maximum {MAX_TICKERS_PER_USER} tickers allowed."})
        return

    invalid = [
        symbol
        for symbol in tickers
        if not validate_symbol(symbol, finnhub_key=finnhub_key, indianapi_key=indianapi_key)
    ]
    if invalid:
        label = ", ".join(invalid)
        send_json(handler, 400, {"ok": False, "error": f"Could not validate: {label}"})
        return

    needs_us = any(market_of(symbol) == "US" for symbol in tickers)
    needs_in = any(market_of(symbol) == "IN" for symbol in tickers)
    if needs_us and not finnhub_key:
        send_json(handler, 503, {"ok": False, "error": "US ticker validation is not configured."})
        return
    if needs_in and not indianapi_key:
        send_json(handler, 503, {"ok": False, "error": "India ticker validation is not configured."})
        return

    try:
        result = subscribe_or_update(
            email,
            tickers,
            api_key,
            int(list_id),
            int(template_id),
            attr_name=BREVO_TICKERS_ATTRIBUTE,
            site_url=os.environ.get("SITE_URL", "").strip() or SITE_URL,
        )
        send_json(handler, 200, result)
    except BrevoError as exc:
        send_json(handler, 400, {"ok": False, "error": str(exc)})
    except Exception:
        traceback.print_exc()
        send_json(handler, 503, {"ok": False, "error": "Could not save your subscription right now."})


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        handle_post(self)
