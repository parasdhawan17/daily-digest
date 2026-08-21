"""Finnhub API helpers."""

from datetime import date, timedelta

import requests

from stock_news.config import (
    FETCH_LIMIT_PER_TICKER,
    FOREIGN_SYMBOL_SUFFIXES,
    PUBLISHER_LOGO_MARKERS,
    TICKER_PATTERN,
    US_SYMBOL_TYPES,
)


def fetch_news(symbol: str, api_key: str, limit: int = FETCH_LIMIT_PER_TICKER) -> list[dict]:
    today = date.today()
    yesterday = today - timedelta(days=1)

    response = requests.get(
        "https://finnhub.io/api/v1/company-news",
        params={
            "symbol": symbol,
            "from": yesterday.isoformat(),
            "to": today.isoformat(),
            "token": api_key,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()[:limit]


def fetch_us_market_holidays(api_key: str) -> list[dict]:
    response = requests.get(
        "https://finnhub.io/api/v1/stock/market-holiday",
        params={"exchange": "US", "token": api_key},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("data") or []


def fetch_quote(symbol: str, api_key: str) -> dict | None:
    response = requests.get(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": symbol, "token": api_key},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not data or data.get("c") in (None, 0):
        return None
    return {"price": data["c"], "change_pct": data.get("dp")}


def fetch_company_logo(symbol: str, api_key: str) -> str | None:
    response = requests.get(
        "https://finnhub.io/api/v1/stock/profile2",
        params={"symbol": symbol, "token": api_key},
        timeout=30,
    )
    response.raise_for_status()
    logo = response.json().get("logo", "").strip()
    return logo or None


def is_usable_article_image(url: str | None) -> bool:
    if not url:
        return False
    lower = url.lower()
    return not any(marker in lower for marker in PUBLISHER_LOGO_MARKERS)


def sanitize_article_image(url: str | None) -> str | None:
    cleaned = (url or "").strip()
    return cleaned if is_usable_article_image(cleaned) else None


def _is_us_symbol(item: dict) -> bool:
    symbol = (item.get("symbol") or item.get("displaySymbol") or "").strip().upper()
    if not symbol:
        return False
    if any(symbol.endswith(suffix) for suffix in FOREIGN_SYMBOL_SUFFIXES):
        return False
    symbol_type = (item.get("type") or "").strip()
    if symbol_type and symbol_type not in US_SYMBOL_TYPES:
        return False
    return True


def search_symbols(query: str, api_key: str, limit: int = 8) -> list[dict]:
    text = query.strip()
    if len(text) < 1:
        return []

    matches = _fetch_search_results(text, api_key, limit=limit, exchange="US")
    if not matches:
        matches = _fetch_search_results(text, api_key, limit=limit, exchange=None)
    return matches


def _fetch_search_results(
    text: str,
    api_key: str,
    *,
    limit: int,
    exchange: str | None,
) -> list[dict]:
    params: dict[str, str] = {"q": text, "token": api_key}
    if exchange:
        params["exchange"] = exchange

    response = requests.get(
        "https://finnhub.io/api/v1/search",
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    results = response.json().get("result") or []

    seen: set[str] = set()
    matches: list[dict] = []
    for item in results:
        if not _is_us_symbol(item):
            continue
        symbol = (item.get("symbol") or item.get("displaySymbol") or "").strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        matches.append(
            {
                "symbol": symbol,
                "name": (item.get("description") or symbol).strip(),
            }
        )
        if len(matches) >= limit:
            break
    return matches


def validate_symbol(symbol: str, api_key: str) -> bool:
    return lookup_symbol(symbol, api_key) is not None


def lookup_symbol(symbol: str, api_key: str) -> dict | None:
    ticker = symbol.strip().upper()
    if not ticker or not fetch_quote(ticker, api_key):
        return None

    name = ticker
    try:
        response = requests.get(
            "https://finnhub.io/api/v1/stock/profile2",
            params={"symbol": ticker, "token": api_key},
            timeout=30,
        )
        response.raise_for_status()
        profile_name = (response.json().get("name") or "").strip()
        if profile_name:
            name = profile_name
    except requests.RequestException:
        pass

    return {"symbol": ticker, "name": name}


def resolve_symbol_query(query: str, api_key: str) -> dict | None:
    text = query.strip()
    if not text:
        return None

    upper = text.upper()
    if TICKER_PATTERN.match(upper):
        direct = lookup_symbol(upper, api_key)
        if direct:
            return direct

    results = search_symbols(text, api_key, limit=8)
    if not results:
        return None

    lower = text.lower()
    best = None
    best_score = -1
    for item in results:
        symbol = item["symbol"]
        name = (item.get("name") or "").lower()
        score = 0
        if symbol == upper:
            score = 100
        elif symbol.startswith(upper):
            score = 80
        elif name.startswith(lower):
            score = 70
        elif lower in name:
            score = 50
        if score > best_score:
            best_score = score
            best = item

    if not best or best_score < 50:
        return None

    return lookup_symbol(best["symbol"], api_key) or best


def story_dedupe_key(item: dict) -> str:
    story_id = item.get("id")
    if story_id is not None:
        return str(story_id)
    headline = item.get("headline", "").strip().lower()
    if headline:
        return headline
    return item.get("url", "").strip().lower()
