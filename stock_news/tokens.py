"""Signed digest URL tokens (HMAC-SHA256)."""

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

from stock_news.config import SITE_URL
from stock_news.relevance import parse_tickers


class TokenError(Exception):
    """Invalid or expired digest token."""


@dataclass(frozen=True)
class DigestTokenClaims:
    tickers: list[str]
    subscriber_id: int | None = None


def _signing_secret() -> str:
    return os.environ.get("DIGEST_SIGNING_SECRET", "").strip()


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign_digest_token(
    tickers: list[str],
    expires_days: int = 14,
    *,
    subscriber_id: int | None = None,
) -> str:
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
    if subscriber_id is not None:
        payload["sub"] = int(subscriber_id)
    payload_b64 = _b64_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64_encode(signature)}"


def verify_digest_claims(token: str) -> DigestTokenClaims:
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

    raw_subscriber_id = payload.get("sub")
    subscriber_id = None
    if raw_subscriber_id is not None:
        try:
            subscriber_id = int(raw_subscriber_id)
        except (TypeError, ValueError):
            raise TokenError("Invalid subscriber")
        if subscriber_id <= 0:
            raise TokenError("Invalid subscriber")

    return DigestTokenClaims(tickers=tickers, subscriber_id=subscriber_id)


def verify_digest_token(token: str) -> list[str]:
    """Verify a token and return its tickers (backward-compatible API)."""
    return verify_digest_claims(token).tickers


def build_digest_url(
    tickers: list[str],
    site_url: str | None = None,
    *,
    subscriber_id: int | None = None,
) -> str:
    base = (site_url or SITE_URL or "").rstrip("/")
    if not base:
        raise ValueError("SITE_URL is not configured")
    token = sign_digest_token(tickers, subscriber_id=subscriber_id)
    return f"{base}/digest?t={token}"
