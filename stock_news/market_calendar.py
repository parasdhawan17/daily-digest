"""US equity market calendar helpers for digest scheduling."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from functools import lru_cache

import requests

from stock_news.config import ET_ZONE, REPO_ROOT
from stock_news.finnhub import fetch_us_market_holidays

HOLIDAYS_CACHE_PATH = REPO_ROOT / "config" / "us_market_holidays.json"


def _is_full_closure(entry: dict) -> bool:
    return not (entry.get("tradingHour") or "").strip()


def _parse_holiday_entry(entry: dict) -> tuple[date, str] | None:
    at_date = (entry.get("atDate") or entry.get("date") or "").strip()
    if not at_date:
        return None
    try:
        holiday_date = date.fromisoformat(at_date)
    except ValueError:
        return None
    name = (entry.get("eventName") or entry.get("name") or "Market holiday").strip()
    return holiday_date, name


def entries_from_finnhub(items: list[dict]) -> dict[str, list[dict[str, str]]]:
    by_year: dict[str, list[dict[str, str]]] = {}
    for item in items:
        if not _is_full_closure(item):
            continue
        parsed = _parse_holiday_entry(item)
        if not parsed:
            continue
        holiday_date, name = parsed
        year_key = str(holiday_date.year)
        entry = {"date": holiday_date.isoformat(), "name": name}
        year_entries = by_year.setdefault(year_key, [])
        if not any(existing["date"] == entry["date"] for existing in year_entries):
            year_entries.append(entry)
    for year_entries in by_year.values():
        year_entries.sort(key=lambda item: item["date"])
    return by_year


def load_holiday_cache() -> dict[str, list[dict[str, str]]]:
    if not HOLIDAYS_CACHE_PATH.is_file():
        return {}
    data = json.loads(HOLIDAYS_CACHE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}

    result: dict[str, list[dict[str, str]]] = {}
    for year_key, entries in data.items():
        if not isinstance(entries, list):
            continue
        normalized: list[dict[str, str]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            date_str = (entry.get("date") or "").strip()
            name = (entry.get("name") or "Market holiday").strip()
            if date_str:
                normalized.append({"date": date_str, "name": name})
        if normalized:
            result[str(year_key)] = sorted(normalized, key=lambda item: item["date"])
    return result


def save_holiday_cache(cache: dict[str, list[dict[str, str]]]) -> None:
    HOLIDAYS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    sorted_cache = {
        year: sorted(entries, key=lambda item: item["date"])
        for year, entries in sorted(cache.items())
    }
    HOLIDAYS_CACHE_PATH.write_text(
        json.dumps(sorted_cache, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _year_holidays_from_cache(
    cache: dict[str, list[dict[str, str]]],
    year: int,
) -> dict[date, str]:
    result: dict[date, str] = {}
    for entry in cache.get(str(year), []):
        try:
            holiday_date = date.fromisoformat(entry["date"])
        except (KeyError, ValueError):
            continue
        result[holiday_date] = entry.get("name", "Market holiday")
    return result


@lru_cache(maxsize=8)
def _cached_year_holidays(year: int, cache_mtime: float) -> dict[date, str]:
    cache = load_holiday_cache()
    return _year_holidays_from_cache(cache, year)


def _cache_mtime() -> float:
    if HOLIDAYS_CACHE_PATH.is_file():
        return HOLIDAYS_CACHE_PATH.stat().st_mtime
    return 0.0


def _fetch_and_cache_year(year: int, api_key: str) -> dict[date, str]:
    try:
        items = fetch_us_market_holidays(api_key)
    except requests.RequestException as exc:
        print(
            f"Warning: could not fetch US market holidays for {year} ({exc}); allowing send.",
            file=sys.stderr,
        )
        return {}

    by_year = entries_from_finnhub(items)
    year_key = str(year)
    if year_key not in by_year:
        print(
            f"Warning: Finnhub returned no full closures for {year}; allowing send.",
            file=sys.stderr,
        )
        return {}

    merged = {**load_holiday_cache(), **by_year}
    try:
        save_holiday_cache(merged)
    except OSError as exc:
        print(f"Warning: could not save holiday cache ({exc}).", file=sys.stderr)

    _cached_year_holidays.cache_clear()
    return _cached_year_holidays(year, _cache_mtime())


def _holiday_lookup(day: date, api_key: str) -> dict[date, str]:
    cache = load_holiday_cache()
    if str(day.year) in cache:
        return _cached_year_holidays(day.year, _cache_mtime())
    return _fetch_and_cache_year(day.year, api_key)


def is_us_trading_day(now: datetime | None = None, *, api_key: str) -> bool:
    return trading_day_skip_reason(now, api_key=api_key) is None


def trading_day_skip_reason(now: datetime | None = None, *, api_key: str) -> str | None:
    current = (now or datetime.now(ET_ZONE)).astimezone(ET_ZONE)
    if current.weekday() >= 5:
        return "weekend"

    today = current.date()
    holidays = _holiday_lookup(today, api_key)
    if today in holidays:
        return f"market holiday: {holidays[today]}"
    return None
