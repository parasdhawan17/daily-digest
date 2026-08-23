"""Signed digest URL tokens (HMAC-SHA256)."""

import base64
import hashlib
import hmac
import json
import os
import time

from stock_news.config import SITE_URL
from stock_news.relevance import parse_tickers


class TokenError(Exception):
    """Invalid or expired digest token."""


def _signing_secret() -> str:
    return os.environ.get("DIGEST_SIGNING_SECRET", "").strip()


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign_digest_token(tickers: list[str], expires_days: int = 14) -> str:
    secret = _signing_secret()
    if not secret:
        raise TokenError("DIGEST_SIGNING_SECRET is not configured")

    tickers = parse_tickers(tickers)
    if not tickers:
        raise TokenError("No valid tickers")

    payload = {
        "tickers": tickers,
        "exp": int(time.time()) + expires_days * 86400,
        "v": 1,
    }
    payload_b64 = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64_encode(signature)}"


def verify_digest_token(token: str) -> list[str]:
    secret = _signing_secret()
    if not secret:
        raise TokenError("DIGEST_SIGNING_SECRET is not configured")

    parts = token.split(".", 1)
    if len(parts) != 2:
        raise TokenError("Invalid token format")

    payload_b64, signature_b64 = parts
    expected = hmac.new(
        secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256
    ).digest()
    try:
        actual = _b64_decode(signature_b64)
    except (ValueError, TypeError):
        raise TokenError("Invalid signature")

    if not hmac.compare_digest(expected, actual):
        raise TokenError("Invalid signature")

    try:
        payload = json.loads(_b64_decode(payload_b64))
    except (json.JSONDecodeError, ValueError, TypeError):
        raise TokenError("Invalid payload")

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < time.time():
        raise TokenError("Token expired")

    tickers = parse_tickers(payload.get("tickers"))
    if not tickers:
        raise TokenError("No tickers in token")

    return tickers


def build_digest_url(tickers: list[str], site_url: str | None = None) -> str:
    base = (site_url or SITE_URL or "").rstrip("/")
    if not base:
        raise ValueError("SITE_URL is not configured")
    token = sign_digest_token(tickers)
    return f"{base}/digest?t={token}"
