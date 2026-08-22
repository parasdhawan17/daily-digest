"""Market prefix helpers for US and India tickers."""

from __future__ import annotations

import re
from typing import Literal

Market = Literal["US", "IN"]

US_TICKER_BODY = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")
IN_TICKER_BODY = re.compile(r"^[A-Z][A-Z0-9&-]{0,19}$")
PREFIXED_TICKER_PATTERN = re.compile(
    r"^(US|IN):([A-Z][A-Z0-9.&-]{0,19})$",
)

MARKET_BADGES: dict[Market, str] = {
    "US": "US",
    "IN": "NSE",
}


def parse_ticker(value: str) -> tuple[Market, str] | None:
    text = value.strip().upper()
    if not text:
        return None

    match = PREFIXED_TICKER_PATTERN.match(text)
    if not match:
        return None

    market = match.group(1)  # type: ignore[assignment]
    symbol = match.group(2)
    if market == "US" and not US_TICKER_BODY.match(symbol):
        return None
    if market == "IN" and not IN_TICKER_BODY.match(symbol):
        return None
    return market, symbol  # type: ignore[return-value]


def normalize_ticker(value: str) -> str | None:
    text = value.strip().upper()
    if not text:
        return None

    parsed = parse_ticker(text)
    if parsed:
        market, symbol = parsed
        return f"{market}:{symbol}"

    if US_TICKER_BODY.match(text):
        return f"US:{text}"
    return None


def display_symbol(value: str) -> str:
    parsed = parse_ticker(value)
    if parsed:
        return parsed[1]
    return value.strip().upper()


def market_of(value: str) -> Market | None:
    parsed = parse_ticker(value)
    if parsed:
        return parsed[0]
    return None


def market_badge(market: Market) -> str:
    return MARKET_BADGES[market]


def is_valid_ticker(value: str) -> bool:
    return normalize_ticker(value) is not None


def bare_symbol(value: str) -> str:
    parsed = parse_ticker(value)
    if parsed:
        return parsed[1]
    return value.strip().upper()


def format_prefixed(market: Market, symbol: str) -> str | None:
    candidate = f"{market}:{symbol.strip().upper()}"
    return candidate if is_valid_ticker(candidate) else None
