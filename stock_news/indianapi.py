"""IndianAPI.in helpers for Indian (NSE/BSE) market data."""

from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

from stock_news.config import (
    FETCH_LIMIT_PER_TICKER,
    IN_ENTITIES_CACHE_PATH,
    IN_NEWS_LOOKBACK_DAYS,
    INDIANAPI_BASE_URL,
)
from stock_news.markets import bare_symbol, format_prefixed

ENTITIES_CACHE_TTL_SECONDS = 24 * 3600
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub("", text).strip()


def _api_root(base_url: str | None = None) -> str:
    return (base_url or INDIANAPI_BASE_URL).rstrip("/")


def _headers(api_key: str) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def _parse_published_at(value: str | int | float | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    try:
        if text.endswith("Z"):
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        try:
            dt = parsedate_to_datetime(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except (TypeError, ValueError, IndexError):
            return None


def _normalize_news_item(item: dict) -> dict:
    headline = _strip_html(
        (
            item.get("title")
            or item.get("headline")
            or item.get("heading")
            or ""
        ).strip()
    )
    summary = _strip_html(
        (
            item.get("summary")
            or item.get("description")
            or item.get("content")
            or item.get("snippet")
            or ""
        ).strip()
    )
    url = (item.get("url") or item.get("link") or item.get("storyUrl") or "").strip()
    source = (item.get("source") or item.get("publisher") or item.get("provider") or "News").strip()
    published = _parse_published_at(
        item.get("published_at")
        or item.get("publishedDate")
        or item.get("date")
        or item.get("datetime")
    )
    story_id = item.get("id")
    if story_id is None and url:
        story_id = url
    return {
        "id": story_id,
        "headline": headline or "News update",
        "summary": summary,
        "url": url,
        "image": (item.get("image") or item.get("imageUrl") or "").strip() or None,
        "source": source,
        "datetime": published,
    }


def _load_entities_cache() -> list[dict]:
    if not IN_ENTITIES_CACHE_PATH.is_file():
        return []
    try:
        data = json.loads(IN_ENTITIES_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("entities") or data.get("data") or []
    return []


def _normalize_entity(item: dict) -> dict | None:
    symbol = (
        item.get("symbol")
        or item.get("exchangeCodeNsi")
        or item.get("tickerId")
        or item.get("ticker")
        or ""
    )
    symbol = bare_symbol(str(symbol).replace(".NS", ""))
    if not symbol:
        return None
    name = (
        item.get("name")
        or item.get("commonName")
        or item.get("companyName")
        or symbol
    ).strip()
    prefixed = format_prefixed("IN", symbol)
    if not prefixed:
        return None
    return {"symbol": prefixed, "name": name, "market": "IN"}


def _fetch_stock(name: str, api_key: str, *, base_url: str | None = None) -> dict | None:
    response = requests.get(
        f"{_api_root(base_url)}/stock",
        params={"name": name},
        headers=_headers(api_key),
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        return None
    if payload.get("error") or payload.get("detail"):
        return None
    return payload


def _stock_name_for_lookup(symbol: str) -> str:
    return bare_symbol(symbol)


def _quote_from_stock(payload: dict) -> dict | None:
    current_price = payload.get("currentPrice") or {}
    price = current_price.get("NSE") or current_price.get("BSE")
    if price in (None, 0):
        return None
    change_pct = payload.get("percentChange")
    return {
        "price": float(price),
        "change_pct": float(change_pct) if change_pct is not None else None,
    }


def _news_from_stock(payload: dict, limit: int) -> list[dict]:
    recent = payload.get("recentNews") or []
    if not isinstance(recent, list):
        return []
    cutoff = date.today() - timedelta(days=IN_NEWS_LOOKBACK_DAYS)
    normalized: list[dict] = []
    for item in recent:
        if not isinstance(item, dict):
            continue
        story = _normalize_news_item(item)
        published = story.get("datetime")
        if published:
            pub_date = datetime.fromtimestamp(published, tz=timezone.utc).date()
            if pub_date < cutoff:
                continue
        normalized.append(story)
    return normalized[:limit]


def fetch_news(
    symbol: str,
    api_key: str,
    limit: int = FETCH_LIMIT_PER_TICKER,
    *,
    base_url: str | None = None,
) -> list[dict]:
    payload = _fetch_stock(_stock_name_for_lookup(symbol), api_key, base_url=base_url)
    if not payload:
        return []
    return _news_from_stock(payload, limit)


def fetch_quote(symbol: str, api_key: str, *, base_url: str | None = None) -> dict | None:
    payload = _fetch_stock(_stock_name_for_lookup(symbol), api_key, base_url=base_url)
    if not payload:
        return None
    return _quote_from_stock(payload)


def fetch_company_logo(symbol: str, api_key: str) -> str | None:
    return None


def _search_industry(
    query: str,
    api_key: str,
    *,
    base_url: str | None = None,
) -> list[dict]:
    response = requests.get(
        f"{_api_root(base_url)}/industry_search",
        params={"query": query},
        headers=_headers(api_key),
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        return []
    return [_normalize_entity(item) for item in payload]


def search_symbols(
    query: str,
    api_key: str,
    limit: int = 8,
    *,
    base_url: str | None = None,
) -> list[dict]:
    text = query.strip()
    if len(text) < 1:
        return []

    lower = text.lower()
    upper = text.upper()
    entities: list[dict] = []

    if api_key:
        try:
            entities = [item for item in _search_industry(text, api_key, base_url=base_url) if item]
        except requests.RequestException:
            entities = []

    if not entities:
        entities = [_normalize_entity(item) for item in _load_entities_cache()]
        entities = [item for item in entities if item]

    scored: list[tuple[int, dict]] = []
    for item in entities:
        if not item:
            continue
        symbol = bare_symbol(item["symbol"])
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
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda row: (-row[0], row[1]["symbol"]))
    seen: set[str] = set()
    matches: list[dict] = []
    for _score, item in scored:
        if item["symbol"] in seen:
            continue
        seen.add(item["symbol"])
        matches.append(item)
        if len(matches) >= limit:
            break
    return matches


def validate_symbol(symbol: str, api_key: str) -> bool:
    return lookup_symbol(symbol, api_key) is not None


def lookup_symbol(symbol: str, api_key: str) -> dict | None:
    bare = bare_symbol(symbol)
    prefixed = format_prefixed("IN", bare)
    if not prefixed or not api_key:
        return None

    try:
        payload = _fetch_stock(_stock_name_for_lookup(bare), api_key)
    except requests.RequestException:
        return None
    if not payload:
        return None

    ticker_id = (payload.get("tickerId") or "").strip().upper()
    if ticker_id and ticker_id != bare:
        return None
    if not _quote_from_stock(payload):
        return None

    name = (payload.get("companyName") or bare).strip()
    return {"symbol": prefixed, "name": name, "market": "IN"}


def resolve_symbol_query(query: str, api_key: str) -> dict | None:
    text = query.strip()
    if not text:
        return None

    upper = text.upper()
    if ":" in upper:
        direct = lookup_symbol(upper, api_key)
        if direct:
            return direct

    prefixed = format_prefixed("IN", upper)
    if prefixed:
        direct = lookup_symbol(prefixed, api_key)
        if direct:
            return direct

    results = search_symbols(text, api_key, limit=8)
    if not results:
        return None

    lower = text.lower()
    best = None
    best_score = -1
    for item in results:
        item_symbol = bare_symbol(item["symbol"])
        name = (item.get("name") or "").lower()
        score = 0
        if item_symbol == upper:
            score = 100
        elif item_symbol.startswith(upper):
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
