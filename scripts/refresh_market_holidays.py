#!/usr/bin/env python3
"""Refresh config/us_market_holidays.json from Finnhub market-holiday API."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


for env_path in (ROOT.parent / "stock-news-bot" / ".env", ROOT / ".env", ROOT / ".env.local"):
    _load_env_file(env_path)

from stock_news.finnhub import fetch_us_market_holidays
from stock_news.market_calendar import (
    HOLIDAYS_CACHE_PATH,
    entries_from_finnhub,
    load_holiday_cache,
    save_holiday_cache,
)


def main() -> None:
    api_key = os.environ.get("FINNHUB_API_KEY", "").strip()
    if not api_key:
        print("Error: FINNHUB_API_KEY is required.", file=sys.stderr)
        sys.exit(1)

    items = fetch_us_market_holidays(api_key)
    fetched = entries_from_finnhub(items)
    if not fetched:
        print("Error: Finnhub returned no full US market closure dates.", file=sys.stderr)
        sys.exit(1)

    existing = load_holiday_cache()
    merged = {**existing}
    added = 0
    for year, entries in fetched.items():
        prior_dates = {entry["date"] for entry in merged.get(year, [])}
        merged[year] = merged.get(year, [])
        for entry in entries:
            if entry["date"] not in prior_dates:
                merged[year].append(entry)
                added += 1
        merged[year] = sorted(merged[year], key=lambda item: item["date"])

    save_holiday_cache(merged)
    years = ", ".join(sorted(merged))
    print(f"Updated {HOLIDAYS_CACHE_PATH} — years: {years}; added {added} date(s).")


if __name__ == "__main__":
    main()
