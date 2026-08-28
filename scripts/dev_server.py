#!/usr/bin/env python3
"""Local dev server: static public/ + subscribe/search API (no Vercel CLI required)."""

import json
import os
import re
import sys
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
sys.path.insert(0, str(ROOT))


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT.parent / "stock-news-bot" / ".env")

from stock_news.brevo import BrevoError, subscribe_or_update
from stock_news.ai_summary import generate_ai_summary
from stock_news.config import (
    BREVO_DOI_TEMPLATE_ID,
    BREVO_LIST_ID,
    BREVO_TICKERS_ATTRIBUTE,
    SITE_URL,
)
from stock_news.digest import collect_digest_data, filter_sections
from stock_news.formatting import format_fetched_at_label
from stock_news.market_data import resolve_symbol_query, search_symbols, validate_symbol
from stock_news.markets import market_of
from stock_news.render import build_digest_error, build_web_digest
from stock_news.relevance import parse_tickers
from stock_news.tokens import TokenError, verify_digest_token

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class DevHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print(f"[dev] {self.address_string()} - {format % args}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/tickers/search":
            self._search(query)
            return
        if path == "/api/tickers/validate":
            self._validate(query)
            return
        if path == "/digest":
            self._digest(query)
            return
        if path == "/api/digest-data":
            from api.digest import handle_data_get
            handle_data_get(self)
            return
        self._serve_static(path)

    def do_POST(self) -> None:
        if urlparse(self.path).path == "/api/digest-ai":
            from api.digest import handle_ai_post
            handle_ai_post(self)
            return
        if urlparse(self.path).path == "/api/subscribe":
            self._subscribe()
            return
        self.send_error(404)

    def _search(self, query: dict) -> None:
        finnhub_key = os.environ.get("FINNHUB_API_KEY", "").strip()
        indianapi_key = os.environ.get("INDIANAPI_API_KEY", "").strip()
        if not finnhub_key and not indianapi_key:
            self._json(503, {"ok": False, "error": "Search is not configured."})
            return
        q = (query.get("q") or [""])[0]
        if len(q.strip()) < 1:
            self._json(400, {"ok": False, "error": "Enter a ticker or company name."})
            return
        try:
            results = search_symbols(
                q,
                finnhub_key=finnhub_key,
                indianapi_key=indianapi_key,
            )
            self._json(200, {"ok": True, "results": results})
        except Exception:
            traceback.print_exc()
            self._json(503, {"ok": False, "error": "Could not search tickers right now."})

    def _validate(self, query: dict) -> None:
        finnhub_key = os.environ.get("FINNHUB_API_KEY", "").strip()
        indianapi_key = os.environ.get("INDIANAPI_API_KEY", "").strip()
        if not finnhub_key and not indianapi_key:
            self._json(503, {"ok": False, "valid": False, "error": "Validation is not configured."})
            return
        ticker = (query.get("symbol") or [""])[0]
        if not ticker.strip():
            self._json(400, {"ok": False, "valid": False, "error": "Enter a ticker or company name."})
            return
        try:
            match = resolve_symbol_query(
                ticker,
                finnhub_key=finnhub_key,
                indianapi_key=indianapi_key,
            )
            if not match:
                self._json(
                    200,
                    {
                        "ok": True,
                        "valid": False,
                        "error": f"Could not find a listing for \"{ticker.strip()}\".",
                    },
                )
                return
            self._json(200, {"ok": True, "valid": True, **match})
        except Exception:
            traceback.print_exc()
            self._json(503, {"ok": False, "valid": False, "error": "Could not validate right now."})

    def _subscribe(self) -> None:
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
            self._json(
                503,
                {
                    "ok": False,
                    "error": "Subscribe is not configured. Set in .env.local: "
                    + ", ".join(missing),
                },
            )
            return
        if not finnhub_key and not indianapi_key:
            self._json(503, {"ok": False, "error": "Ticker validation is not configured."})
            return

        try:
            payload = self._read_json()
        except ValueError:
            self._json(400, {"ok": False, "error": "Invalid request body."})
            return

        email = str(payload.get("email") or "").strip().lower()
        if not email or not EMAIL_PATTERN.match(email):
            self._json(400, {"ok": False, "error": "Enter a valid email address."})
            return

        raw_tickers = payload.get("tickers")
        if not isinstance(raw_tickers, list):
            self._json(400, {"ok": False, "error": "Select at least one ticker."})
            return

        tickers = parse_tickers([str(item) for item in raw_tickers])
        if not tickers:
            self._json(400, {"ok": False, "error": "Select at least one valid ticker."})
            return
        invalid = [
            symbol
            for symbol in tickers
            if not validate_symbol(symbol, finnhub_key=finnhub_key, indianapi_key=indianapi_key)
        ]
        if invalid:
            self._json(400, {"ok": False, "error": f"Could not validate: {', '.join(invalid)}"})
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
            self._json(200, result)
        except BrevoError as exc:
            self._json(400, {"ok": False, "error": str(exc)})
        except Exception:
            traceback.print_exc()
            self._json(503, {"ok": False, "error": "Could not save your subscription right now."})

    def _digest(self, query: dict) -> None:
        # Keep local behavior aligned with the Vercel progressive digest path.
        from api.digest import handle_get
        handle_get(self)
        return

        token = (query.get("t") or [None])[0]
        if not token:
            html = build_digest_error(
                "Missing link",
                "Open the digest link from your email, or subscribe to get personalized digests.",
            )
            self._html(400, html)
            return

        try:
            tickers = verify_digest_token(token)
        except TokenError as exc:
            message = str(exc)
            if "expired" in message.lower():
                title, detail = "Link expired", "Open the latest email and use the link there."
            else:
                title, detail = "Invalid link", "This digest link is not valid."
            html = build_digest_error(title, "We couldn't open this digest.", detail=detail)
            status = 403 if "expired" in message.lower() else 400
            self._html(status, html)
            return

        finnhub_key = os.environ.get("FINNHUB_API_KEY", "").strip()
        indianapi_key = os.environ.get("INDIANAPI_API_KEY", "").strip()
        missing = []
        if any(market_of(symbol) == "US" for symbol in tickers) and not finnhub_key:
            missing.append("FINNHUB_API_KEY")
        if any(market_of(symbol) == "IN" for symbol in tickers) and not indianapi_key:
            missing.append("INDIANAPI_API_KEY")
        if missing:
            html = build_digest_error(
                "Service unavailable",
                "The digest service is not configured.",
                detail="Missing: " + ", ".join(missing),
            )
            self._html(503, html)
            return

        try:
            sections, _ = collect_digest_data(
                tickers,
                finnhub_key=finnhub_key,
                indianapi_key=indianapi_key,
                include_earnings=True,
                include_price_ranges=True,
                include_indian_media=True,
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
            self._html(200, html)
        except Exception:
            traceback.print_exc()
            html = build_digest_error(
                "Something went wrong",
                "We couldn't load your digest right now.",
                detail="Please try again in a few minutes.",
            )
            self._html(503, html)

    def _serve_static(self, path: str) -> None:
        if path == "/":
            path = "/index.html"
        elif path == "/welcome":
            path = "/welcome.html"
        file_path = PUBLIC / path.lstrip("/")
        if not file_path.is_file():
            self.send_error(404)
            return
        content = file_path.read_bytes()
        content_type = "text/html"
        if file_path.suffix == ".js":
            content_type = "application/javascript"
        elif file_path.suffix == ".css":
            content_type = "text/css"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

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

    def _html(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = int(os.environ.get("PORT", "3000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), DevHandler)
    print(f"Daily Digest dev server: http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
