"""Digest page handler."""

import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api._responses import read_json, send_html, send_json
from stock_news.auth import AuthError, get_session, subscription, require_csrf
from stock_news.ai_summary import generate_ai_summary
from stock_news.financial_health_ai import generate_financial_health_summaries
from stock_news.design import resolve_design
from stock_news.brevo import BrevoError, get_contact
from stock_news.config import BREVO_TICKERS_ATTRIBUTE
from stock_news.digest import collect_digest_data, filter_sections
from stock_news.formatting import format_fetched_at_label
from stock_news.markets import market_of
from stock_news.relevance import parse_tickers
from stock_news.render import build_digest_error, build_web_digest, build_web_section
from stock_news.tokens import TokenError, verify_digest_claims, verify_digest_token


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
        identity = get_session(handler)
        state = subscription(identity) if identity else None
        return ("session", state['tickers']) if state and not state['needs_subscription'] else (None, None)
    try:
        return token, verify_digest_token(token)
    except TokenError:
        return token, None


def handle_get(handler: BaseHTTPRequestHandler) -> None:
    query = parse_qs(urlparse(handler.path).query)
    token = (query.get("t") or [None])[0]

    if not token:
        try:
            identity = get_session(handler)
            if not identity:
                handler.send_response(302)
                handler.send_header("Location", "/?signin=1")
                handler.send_header("Cache-Control", "no-store")
                handler.end_headers()
                return
            state = subscription(identity)
            if state['needs_subscription']:
                handler.send_response(302)
                handler.send_header("Location", "/#subscribe")
                handler.send_header("Cache-Control", "no-store")
                handler.end_headers()
                return
            tickers = state['tickers']
        except AuthError as exc:
            send_html(handler, 403, build_digest_error("Sign in again", str(exc)))
            return
        except Exception:
            send_html(handler, 503, build_digest_error("Service unavailable", "Could not load your subscription. Please try again."))
            return
    else:
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
        subscribe_enabled_override=True if not token else None,
        design=(query.get("design") or [None])[0],
    )
    send_html(handler, 200, html)


def handle_data_get(handler: BaseHTTPRequestHandler) -> None:
    """Return one ticker's data so the browser can progressively render it."""
    try:
        token, tickers = _verify_token(handler)
    except AuthError as exc:
        send_json(handler, 403, {"ok": False, "error": str(exc)})
        return
    except Exception:
        send_json(handler, 503, {"ok": False, "error": "Could not load your subscription."})
        return
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
            include_financial_health=resolve_design((query.get("design") or [None])[0]) == "modern",
        )
        section = filter_sections(sections, [ticker])[0]
        send_json(handler, 200, {"ok": True, "section": section, "html": build_web_section(section, design=(query.get("design") or [None])[0])})
    except Exception:
        traceback.print_exc()
        send_json(handler, 503, {"ok": False, "error": "Could not load this ticker right now."})


def handle_ai_post(handler: BaseHTTPRequestHandler) -> None:
    """Generate the optional AI briefing after the visible sections are loaded."""
    try:
        _token, tickers = _verify_token(handler)
        if _token == "session":
            require_csrf(handler)
    except AuthError as exc:
        send_json(handler, 403, {"ok": False, "error": str(exc)})
        return
    except Exception:
        send_json(handler, 503, {"ok": False, "error": "Could not load your subscription."})
        return
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
        results = {"ai_summary": None, "financial_health_summaries": {}}
        with ThreadPoolExecutor(max_workers=2) as executor:
            jobs = {"ai_summary": executor.submit(generate_ai_summary, safe_sections),
                    "financial_health_summaries": executor.submit(generate_financial_health_summaries, safe_sections)}
            for name, job in jobs.items():
                try:
                    results[name] = job.result()
                except Exception:
                    traceback.print_exc()
        send_json(handler, 200, {"ok": True, **results})
    except Exception:
        traceback.print_exc()
        send_json(handler, 200, {"ok": True, "ai_summary": None, "financial_health_summaries": {}})


def handle_subscription_get(handler: BaseHTTPRequestHandler) -> None:
    """Return the saved subscription associated with a signed digest link."""
    query = parse_qs(urlparse(handler.path).query)
    token = (query.get("t") or [None])[0]
    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    if not token:
        try:
            identity = get_session(handler)
            if not identity:
                send_json(handler, 401, {"ok": False, "error": "Sign in to load your subscription."})
                return
            send_json(handler, 200, subscription(identity))
        except AuthError as exc:
            send_json(handler, 403, {"ok": False, "error": str(exc)})
        except Exception:
            send_json(handler, 503, {"ok": False, "error": "Could not load your subscription."})
        return
    try:
        claims = verify_digest_claims(token)
    except TokenError:
        send_json(handler, 403, {"ok": False, "error": "Invalid digest link."})
        return

    # Older links did not carry a contact identifier. They can still prefill the
    # tickers embedded in the digest, while leaving email entry to the user.
    if claims.subscriber_id is None:
        send_json(handler, 200, {"ok": True, "email": "", "tickers": claims.tickers})
        return
    if not api_key:
        send_json(handler, 503, {"ok": False, "error": "Subscription lookup is unavailable."})
        return

    try:
        contact = get_contact(claims.subscriber_id, api_key)
        if not contact or contact.get("emailBlacklisted"):
            send_json(handler, 404, {"ok": False, "error": "Subscription not found."})
            return
        attributes = contact.get("attributes") or {}
        raw_tickers = next(
            (
                value
                for key, value in attributes.items()
                if str(key).upper() == BREVO_TICKERS_ATTRIBUTE.upper()
            ),
            "",
        )
        send_json(
            handler,
            200,
            {
                "ok": True,
                "email": str(contact.get("email") or "").strip().lower(),
                "tickers": parse_tickers(raw_tickers) or claims.tickers,
            },
        )
    except BrevoError:
        send_json(handler, 503, {"ok": False, "error": "Could not load your subscription."})
    except Exception:
        traceback.print_exc()
        send_json(handler, 503, {"ok": False, "error": "Could not load your subscription."})


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        handle_get(self)
