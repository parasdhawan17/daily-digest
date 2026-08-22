"""India (NSE) market calendar helpers for digest scheduling."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from functools import lru_cache

from stock_news.config import IST_ZONE, REPO_ROOT

IN_HOLIDAYS_CACHE_PATH = REPO_ROOT / "config" / "in_market_holidays.json"


def load_holiday_cache() -> dict[str, list[dict[str, str]]]:
    if not IN_HOLIDAYS_CACHE_PATH.is_file():
        return {}
    data = json.loads(IN_HOLIDAYS_CACHE_PATH.read_text(encoding="utf-8"))
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
    IN_HOLIDAYS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    sorted_cache = {
        year: sorted(entries, key=lambda item: item["date"])
        for year, entries in sorted(cache.items())
    }
    IN_HOLIDAYS_CACHE_PATH.write_text(
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
    if IN_HOLIDAYS_CACHE_PATH.is_file():
        return IN_HOLIDAYS_CACHE_PATH.stat().st_mtime
    return 0.0


def _holiday_lookup(day: date) -> dict[date, str]:
    return _cached_year_holidays(day.year, _cache_mtime())


def in_trading_day_skip_reason(now: datetime | None = None) -> str | None:
    current = (now or datetime.now(IST_ZONE)).astimezone(IST_ZONE)
    if current.weekday() >= 5:
        return "weekend"

    today = current.date()
    holidays = _holiday_lookup(today)
    if today in holidays:
        return f"market holiday: {holidays[today]}"
    return None


def is_in_trading_day(now: datetime | None = None) -> bool:
    return in_trading_day_skip_reason(now) is None
