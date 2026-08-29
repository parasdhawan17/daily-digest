"""Route market data requests to Finnhub (US) or IndianAPI.in (India)."""

from __future__ import annotations

from stock_news import finnhub, indianapi
from stock_news.markets import Market, bare_symbol, format_prefixed, market_of, normalize_ticker


def _us_symbol(prefixed: str) -> str:
    return bare_symbol(prefixed)


def _require_market(prefixed: str) -> Market:
    market = market_of(prefixed)
    if not market:
        raise ValueError(f"Invalid ticker: {prefixed}")
    return market


def fetch_news(
    prefixed_ticker: str,
    *,
    finnhub_key: str,
    indianapi_key: str,
) -> list[dict]:
    market = _require_market(prefixed_ticker)
    if market == "US":
        return finnhub.fetch_news(_us_symbol(prefixed_ticker), finnhub_key)
    return indianapi.fetch_news(_us_symbol(prefixed_ticker), indianapi_key)


def fetch_quote(
    prefixed_ticker: str,
    *,
    finnhub_key: str,
    indianapi_key: str,
) -> dict | None:
    market = _require_market(prefixed_ticker)
    if market == "US":
        return finnhub.fetch_quote(_us_symbol(prefixed_ticker), finnhub_key)
    return indianapi.fetch_quote(_us_symbol(prefixed_ticker), indianapi_key)


def fetch_quote_and_news(
    prefixed_ticker: str,
    *,
    finnhub_key: str,
    indianapi_key: str,
) -> tuple[dict | None, list[dict]]:
    """Fetch quote and news together when the provider exposes one payload."""
    market = _require_market(prefixed_ticker)
    symbol = _us_symbol(prefixed_ticker)
    if market == "US":
        return finnhub.fetch_quote(symbol, finnhub_key), finnhub.fetch_news(symbol, finnhub_key)
    return indianapi.fetch_quote_and_news(symbol, indianapi_key)


def fetch_company_logo(
    prefixed_ticker: str,
    *,
    finnhub_key: str,
    indianapi_key: str,
) -> str | None:
    market = _require_market(prefixed_ticker)
    if market == "US":
        return finnhub.fetch_company_logo(_us_symbol(prefixed_ticker), finnhub_key)
    return indianapi.fetch_company_logo(_us_symbol(prefixed_ticker), indianapi_key)


def fetch_all_time_high(
    prefixed_ticker: str,
    *,
    finnhub_key: str,
    indianapi_key: str,
) -> float | None:
    """Return the highest available historical price for Indian stocks only."""
    market = _require_market(prefixed_ticker)
    if market == "IN":
        return indianapi.fetch_all_time_high(_us_symbol(prefixed_ticker), indianapi_key)
    return None


def fetch_earnings_history(
    prefixed_ticker: str,
    *,
    finnhub_key: str,
    indianapi_key: str,
    limit: int = 4,
) -> list[dict]:
    """Return normalized reported earnings history for the requested market."""
    market = _require_market(prefixed_ticker)
    if market == "US":
        return finnhub.fetch_earnings_history(
            _us_symbol(prefixed_ticker),
            finnhub_key,
            limit=limit,
        )
    return indianapi.fetch_earnings_history(
        _us_symbol(prefixed_ticker),
        indianapi_key,
        limit=limit,
    )


def fetch_upcoming_earnings(
    prefixed_ticker: str,
    *,
    finnhub_key: str,
    indianapi_key: str,
    lookahead_days: int = 90,
) -> dict | None:
    """Return the next US earnings-calendar event; India is unsupported."""
    market = _require_market(prefixed_ticker)
    if market == "US":
        return finnhub.fetch_upcoming_earnings(
            _us_symbol(prefixed_ticker),
            finnhub_key,
            lookahead_days=lookahead_days,
        )
    return None


def search_symbols(
    query: str,
    *,
    finnhub_key: str,
    indianapi_key: str,
    limit: int = 8,
    market: Market | None = None,
) -> list[dict]:
    text = query.strip()
    if not text:
        return []

    per_market = max(4, limit // 2) if market is None else limit
    results: list[dict] = []

    if market in (None, "US") and finnhub_key:
        for item in finnhub.search_symbols(text, finnhub_key, limit=per_market):
            bare = item["symbol"].strip().upper()
            prefixed = format_prefixed("US", bare)
            if prefixed:
                results.append(
                    {
                        "symbol": prefixed,
                        "name": item.get("name") or bare,
                        "market": "US",
                    }
                )

    if market in (None, "IN"):
        for item in indianapi.search_symbols(text, indianapi_key or "", limit=per_market):
            results.append(
                {
                    "symbol": item["symbol"],
                    "name": item.get("name") or bare_symbol(item["symbol"]),
                    "market": "IN",
                }
            )

    return results[:limit]


def validate_symbol(
    prefixed_ticker: str,
    *,
    finnhub_key: str,
    indianapi_key: str,
) -> bool:
    normalized = normalize_ticker(prefixed_ticker)
    if not normalized:
        return False
    market = _require_market(normalized)
    if market == "US":
        return finnhub.validate_symbol(_us_symbol(normalized), finnhub_key)
    return indianapi.validate_symbol(_us_symbol(normalized), indianapi_key)


def lookup_symbol(
    prefixed_ticker: str,
    *,
    finnhub_key: str,
    indianapi_key: str,
) -> dict | None:
    normalized = normalize_ticker(prefixed_ticker)
    if not normalized:
        return None
    market = _require_market(normalized)
    if market == "US":
        match = finnhub.lookup_symbol(_us_symbol(normalized), finnhub_key)
        if match:
            return {
                "symbol": normalized,
                "name": match.get("name") or _us_symbol(normalized),
                "market": "US",
            }
        return None
    match = indianapi.lookup_symbol(_us_symbol(normalized), indianapi_key)
    if match:
        return {
            "symbol": normalized,
            "name": match.get("name") or _us_symbol(normalized),
            "market": "IN",
        }
    return None


def resolve_symbol_query(
    query: str,
    *,
    finnhub_key: str,
    indianapi_key: str,
) -> dict | None:
    text = query.strip()
    if not text:
        return None

    upper = text.upper()
    if upper.startswith("US:") or upper.startswith("IN:"):
        return lookup_symbol(upper, finnhub_key=finnhub_key, indianapi_key=indianapi_key)

    us_prefixed = format_prefixed("US", upper)
    if us_prefixed and finnhub_key:
        us_match = lookup_symbol(us_prefixed, finnhub_key=finnhub_key, indianapi_key=indianapi_key)
        if us_match:
            return us_match

    in_prefixed = format_prefixed("IN", upper)
    if in_prefixed and indianapi_key:
        in_match = lookup_symbol(in_prefixed, finnhub_key=finnhub_key, indianapi_key=indianapi_key)
        if in_match:
            return in_match

    results = search_symbols(text, finnhub_key=finnhub_key, indianapi_key=indianapi_key, limit=8)
    if not results:
        return None

    lower = text.lower()
    best = None
    best_score = -1
    for item in results:
        item_symbol = item["symbol"]
        bare = bare_symbol(item_symbol)
        name = (item.get("name") or "").lower()
        score = 0
        if bare == upper:
            score = 100
        elif bare.startswith(upper):
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

    return lookup_symbol(best["symbol"], finnhub_key=finnhub_key, indianapi_key=indianapi_key) or best
