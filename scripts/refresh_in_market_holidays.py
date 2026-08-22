#!/usr/bin/env python3
"""Refresh config/in_market_holidays.json from NSE India holiday API."""

import json
import sys
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stock_news.in_market_calendar import IN_HOLIDAYS_CACHE_PATH, load_holiday_cache, save_holiday_cache

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/",
}


def fetch_nse_holidays(year: int) -> list[dict[str, str]]:
    session = requests.Session()
    session.get("https://www.nseindia.com/", headers=NSE_HEADERS, timeout=30)
    response = session.get(
        "https://www.nseindia.com/api/holiday-master",
        params={"type": "trading"},
        headers=NSE_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    entries: list[dict[str, str]] = []
    for block in payload.values():
        if not isinstance(block, list):
            continue
        for item in block:
            trading_date = (item.get("tradingDate") or item.get("date") or "").strip()
            description = (item.get("description") or item.get("purpose") or "Market holiday").strip()
            if not trading_date:
                continue
            try:
                holiday_date = date.fromisoformat(trading_date[:10])
            except ValueError:
                continue
            if holiday_date.year != year:
                continue
            entries.append({"date": holiday_date.isoformat(), "name": description})

    entries.sort(key=lambda item: item["date"])
    return entries


def main() -> None:
    year = date.today().year
    try:
        fetched = fetch_nse_holidays(year)
    except requests.RequestException as exc:
        print(f"Error: could not fetch NSE holidays for {year}: {exc}", file=sys.stderr)
        sys.exit(1)

    if not fetched:
        print(f"Error: NSE returned no holidays for {year}.", file=sys.stderr)
        sys.exit(1)

    merged = {**load_holiday_cache(), str(year): fetched}
    save_holiday_cache(merged)
    print(f"Wrote {len(fetched)} NSE holidays for {year} to {IN_HOLIDAYS_CACHE_PATH}")


if __name__ == "__main__":
    main()
