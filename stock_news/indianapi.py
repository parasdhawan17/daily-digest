"""IndianAPI.in helpers for Indian (NSE/BSE) market data."""

from __future__ import annotations

import base64
import binascii
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
_ALLOWED_LOGO_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
_MAX_LOGO_BYTES = 2 * 1024 * 1024
_FMP_LOGO_ROOT = "https://financialmodelingprep.com/image-stock"


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
        or item.get("pub_date")
        or item.get("publishedDate")
        or item.get("date")
        or item.get("datetime")
    )
    story_id = item.get("id")
    if story_id is None and url:
        story_id = url
    image = _news_image(item)
    return {
        "id": story_id,
        "headline": headline or "News update",
        "summary": summary,
        "url": url,
        "image": image,
        "source": source,
        "datetime": published,
    }


def _news_image(item: dict) -> str | None:
    lead_media = item.get("leadMedia")
    lead_images: dict = {}
    if isinstance(lead_media, dict):
        image = lead_media.get("image")
        if isinstance(image, dict):
            images = image.get("images")
            if isinstance(images, dict):
                lead_images = images

    candidates = (
        lead_images.get("bigImage"),
        lead_images.get("thumbnailImage"),
        item.get("listimage"),
        item.get("thumbnailImage"),
        item.get("image"),
        item.get("image_url"),
        item.get("imageUrl"),
        item.get("thumbnail_url"),
        item.get("thumbnail"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


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
        "year_high": _as_float(payload.get("yearHigh")),
    }


def _as_float(value: object) -> float | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _as_financial_float(value: object) -> float | None:
    if isinstance(value, bool) or value in (None, "", "—", "-"):
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _field_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _financial_series(payload: dict, *names: str) -> dict:
    wanted = {_field_key(name) for name in names}
    for key, value in payload.items():
        if _field_key(key) in wanted and isinstance(value, dict):
            return value
    return {}


def _series_value(series: dict, period_label: str) -> object:
    for key, value in series.items():
        if str(key).strip() == period_label:
            return value
    return None


def _quarter_metadata(period_label: str) -> tuple[datetime | None, str, int, int]:
    parsed = None
    for date_format in ("%b %Y", "%B %Y"):
        try:
            parsed = datetime.strptime(period_label.strip(), date_format)
            break
        except ValueError:
            continue
    if parsed is None:
        return None, period_label, 0, 0

    quarter_by_month = {3: 4, 6: 1, 9: 2, 12: 3}
    fiscal_quarter = quarter_by_month.get(parsed.month, 0)
    fiscal_year = parsed.year + 1 if parsed.month >= 4 else parsed.year
    label = (
        f"Q{fiscal_quarter} FY{str(fiscal_year)[-2:]}"
        if fiscal_quarter
        else period_label
    )
    return parsed, label, fiscal_year, fiscal_quarter


def _earnings_from_historical_stats(payload: object, limit: int) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("data"), dict):
        payload = payload["data"]

    series = {
        "sales": _financial_series(payload, "Sales", "Revenue"),
        "expenses": _financial_series(payload, "Expenses"),
        "operating_profit": _financial_series(payload, "Operating Profit"),
        "opm_pct": _financial_series(payload, "OPM %", "Operating Profit Margin"),
        "net_profit": _financial_series(payload, "Net Profit", "Net Income"),
        "actual": _financial_series(payload, "EPS in Rs", "EPS", "Earnings Per Share"),
    }
    periods = {
        str(period).strip()
        for values in series.values()
        for period in values
        if str(period).strip()
    }

    quarters: list[dict] = []
    for period_label in periods:
        parsed, label, fiscal_year, fiscal_quarter = _quarter_metadata(period_label)
        if parsed is None:
            continue
        quarter = {
            "mode": "reported",
            "period": parsed.strftime("%Y-%m-%d"),
            "period_label": period_label,
            "label": label,
            "fiscal_year": fiscal_year,
            "fiscal_quarter": fiscal_quarter,
        }
        for field, values in series.items():
            quarter[field] = _as_financial_float(_series_value(values, period_label))
        if any(quarter.get(field) is not None for field in series):
            quarters.append(quarter)

    quarters.sort(key=lambda item: item["period"])
    return quarters[-max(1, limit):]


def _all_time_high_from_history(payload: object) -> float | None:
    if not isinstance(payload, dict):
        return None
    datasets = payload.get("datasets")
    if not isinstance(datasets, list):
        return None

    highs: list[float] = []
    for dataset in datasets:
        if not isinstance(dataset, dict):
            continue
        metric = str(dataset.get("metric") or "").strip().lower()
        label = str(dataset.get("label") or "").strip().lower()
        if metric != "price" and not label.startswith("price"):
            continue
        values = dataset.get("values")
        if not isinstance(values, list):
            continue
        for row in values:
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                continue
            price = _as_float(row[1])
            if price is not None:
                highs.append(price)
    return max(highs, default=None)


def _news_items(payload: object) -> list:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("recentNews", "news", "articles", "data", "results"):
        items = payload.get(key)
        if isinstance(items, list):
            return items
    return []


def _normalize_news_items(items: list, limit: int) -> list[dict]:
    cutoff = date.today() - timedelta(days=IN_NEWS_LOOKBACK_DAYS)
    normalized: list[dict] = []
    for item in items:
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


def _news_from_stock(payload: dict, limit: int) -> list[dict]:
    return _normalize_news_items(_news_items(payload), limit)


def fetch_quote_and_news(
    symbol: str,
    api_key: str,
    limit: int = FETCH_LIMIT_PER_TICKER,
    *,
    base_url: str | None = None,
) -> tuple[dict | None, list[dict]]:
    """Fetch and normalize the stock-plan payload with one API request."""
    payload = _fetch_stock(_stock_name_for_lookup(symbol), api_key, base_url=base_url)
    if not payload:
        return None, []
    return _quote_from_stock(payload), _news_from_stock(payload, limit)


def fetch_news(
    symbol: str,
    api_key: str,
    limit: int = FETCH_LIMIT_PER_TICKER,
    *,
    base_url: str | None = None,
) -> list[dict]:
    api_root = _api_root(base_url)
    if api_root != "https://stock.indianapi.in":
        try:
            response = requests.get(
                f"{api_root}/company_news",
                params={"stock_name": _stock_name_for_lookup(symbol)},
                headers=_headers(api_key),
                timeout=30,
            )
            response.raise_for_status()
            richer_news = _normalize_news_items(_news_items(response.json()), limit)
            if richer_news:
                return richer_news
        except (requests.RequestException, ValueError):
            pass

    payload = _fetch_stock(_stock_name_for_lookup(symbol), api_key, base_url=base_url)
    if not payload:
        return []
    return _news_from_stock(payload, limit)


def fetch_quote(symbol: str, api_key: str, *, base_url: str | None = None) -> dict | None:
    payload = _fetch_stock(_stock_name_for_lookup(symbol), api_key, base_url=base_url)
    if not payload:
        return None
    return _quote_from_stock(payload)


def fetch_all_time_high(
    symbol: str,
    api_key: str,
    *,
    base_url: str | None = None,
) -> float | None:
    response = requests.get(
        f"{_api_root(base_url)}/historical_data",
        params={
            "stock_name": _stock_name_for_lookup(symbol),
            "period": "max",
            "filter": "price",
        },
        headers=_headers(api_key),
        timeout=30,
    )
    response.raise_for_status()
    return _all_time_high_from_history(response.json())


def fetch_earnings_history(
    symbol: str,
    api_key: str,
    limit: int = 4,
    *,
    base_url: str | None = None,
) -> list[dict]:
    response = requests.get(
        f"{_api_root(base_url)}/historical_stats",
        params={
            "stock_name": _stock_name_for_lookup(symbol),
            "stats": "quarter_results",
        },
        headers=_headers(api_key),
        timeout=30,
    )
    response.raise_for_status()
    return _earnings_from_historical_stats(response.json(), limit)


def fetch_company_logo(
    symbol: str,
    api_key: str,
    *,
    base_url: str | None = None,
) -> str | None:
    api_root = _api_root(base_url)
    if api_root != "https://stock.indianapi.in":
        try:
            response = requests.get(
                f"{api_root}/logo",
                params={"stock_name": _stock_name_for_lookup(symbol)},
                headers=_headers(api_key),
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            logo = _logo_data_url(payload)
            if logo:
                return logo
        except (requests.RequestException, ValueError):
            pass

    return _fetch_public_nse_logo(symbol)


def _logo_data_url(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    content_type = str(
        payload.get("content_type") or payload.get("contentType") or ""
    ).strip().lower().split(";", 1)[0]
    encoded = str(
        payload.get("base64_image") or payload.get("base64Image") or ""
    ).strip()
    encoded = re.sub(r"\s+", "", encoded)
    if content_type not in _ALLOWED_LOGO_CONTENT_TYPES or not encoded:
        return None
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not decoded or len(decoded) > _MAX_LOGO_BYTES:
        return None
    return f"data:{content_type};base64,{encoded}"


def _fetch_public_nse_logo(symbol: str) -> str | None:
    stock_symbol = _stock_name_for_lookup(symbol)
    if not re.fullmatch(r"[A-Z0-9&-]+", stock_symbol):
        return None
    response = requests.get(
        f"{_FMP_LOGO_ROOT}/{stock_symbol}.NS.png",
        headers={"Accept": "image/png,image/jpeg,image/webp,image/gif"},
        timeout=15,
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower().split(";", 1)[0]
    content = response.content
    if content_type not in _ALLOWED_LOGO_CONTENT_TYPES:
        return None
    if not content or len(content) > _MAX_LOGO_BYTES:
        return None
    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


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
