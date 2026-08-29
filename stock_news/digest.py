"""Collect market data and prepare digest layout."""

import math
from datetime import date

import requests

from stock_news.config import HEADLINES_PER_TICKER, MIN_RELEVANCE_SCORE
from stock_news.finnhub import story_dedupe_key
from stock_news.market_data import (
    fetch_all_time_high,
    fetch_basic_financials,
    fetch_company_logo,
    fetch_earnings_history,
    fetch_upcoming_earnings,
    fetch_news,
    fetch_quote,
    fetch_quote_and_news,
)
from stock_news.markets import display_symbol, market_badge, market_of
from stock_news.relevance import relevance_score, select_stories, select_web_stories


def filter_sections(sections: list[dict], tickers: list[str]) -> list[dict]:
    ticker_set = set(tickers)
    return [section for section in sections if section["ticker"] in ticker_set]


def _period_label(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        return value
    return parsed.strftime("%d %b %Y").lstrip("0")


def build_earnings_history(quarters: list[dict]) -> dict | None:
    """Build the comparison view model used by the web earnings panel."""
    if not quarters:
        return None

    ordered = sorted(
        (dict(item) for item in quarters if isinstance(item, dict)),
        key=lambda item: (
            str(item.get("period") or ""),
            int(item.get("fiscal_year") or 0),
            int(item.get("fiscal_quarter") or 0),
        ),
    )[-4:]
    if not ordered:
        return None

    counts = {"beat": 0, "miss": 0, "inline": 0, "unavailable": 0}
    surprise_values: list[float] = []
    for item in ordered:
        result = item.get("result")
        if result not in counts:
            result = "unavailable"
            item["result"] = result
        counts[result] += 1
        surprise_pct = item.get("surprise_pct")
        if isinstance(surprise_pct, (int, float)) and not isinstance(surprise_pct, bool):
            surprise_values.append(abs(float(surprise_pct)))
        item["period_label"] = _period_label(str(item.get("period") or ""))
        item["latest"] = False

    max_surprise = max(surprise_values, default=0.0)
    chart_scale = max(5.0, math.ceil(max_surprise / 5.0) * 5.0)
    for item in ordered:
        surprise_pct = item.get("surprise_pct")
        if isinstance(surprise_pct, (int, float)) and not isinstance(surprise_pct, bool):
            item["chart_width_pct"] = min(100.0, abs(float(surprise_pct)) / chart_scale * 100.0)
        else:
            item["chart_width_pct"] = 0.0
    ordered[-1]["latest"] = True

    summary_parts: list[str] = []
    if counts["beat"]:
        summary_parts.append(f"{counts['beat']} {'beat' if counts['beat'] == 1 else 'beats'}")
    if counts["miss"]:
        summary_parts.append(f"{counts['miss']} {'miss' if counts['miss'] == 1 else 'misses'}")
    if counts["inline"]:
        summary_parts.append(f"{counts['inline']} in line")
    if counts["unavailable"]:
        summary_parts.append(f"{counts['unavailable']} unavailable")
    if not summary_parts:
        summary_parts.append(f"{len(ordered)} reported quarters")

    return {
        "quarters": ordered,
        "counts": counts,
        "summary_label": " · ".join(summary_parts),
        "chart_scale_pct": chart_scale,
    }


def build_indian_earnings_history(quarters: list[dict]) -> dict | None:
    """Build the reported-results view model for Indian web ticker cards."""
    ordered = sorted(
        (dict(item) for item in quarters if isinstance(item, dict)),
        key=lambda item: str(item.get("period") or ""),
    )[-4:]
    if not ordered:
        return None

    eps_values = [
        abs(float(item["actual"]))
        for item in ordered
        if isinstance(item.get("actual"), (int, float))
        and not isinstance(item.get("actual"), bool)
    ]
    chart_scale = max(eps_values, default=0.0)
    for item in ordered:
        actual = item.get("actual")
        item["latest"] = False
        if isinstance(actual, (int, float)) and not isinstance(actual, bool):
            item["direction"] = "positive" if actual > 0 else "negative" if actual < 0 else "flat"
            item["chart_width_pct"] = (
                min(100.0, abs(float(actual)) / chart_scale * 100.0)
                if chart_scale > 0
                else 0.0
            )
        else:
            item["direction"] = "unavailable"
            item["chart_width_pct"] = 0.0
    ordered[-1]["latest"] = True

    latest_eps = ordered[-1].get("actual")
    summary_label = (
        f"Latest EPS ₹{float(latest_eps):.2f}"
        if isinstance(latest_eps, (int, float)) and not isinstance(latest_eps, bool)
        else f"{len(ordered)} reported quarters"
    )
    return {
        "mode": "reported",
        "quarters": ordered,
        "summary_label": summary_label,
        "chart_scale_value": chart_scale,
    }


def build_price_ranges(
    current_price: object,
    *,
    year_high: object = None,
    all_time_high: object = None,
) -> dict | None:
    """Build compact high-watermark metrics for an Indian web ticker card."""
    if not isinstance(current_price, (int, float)) or isinstance(current_price, bool):
        return None
    current = float(current_price)
    if current <= 0:
        return None

    def metric(value: object) -> dict | None:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None
        high = max(current, float(value))
        if high <= 0:
            return None
        return {
            "value": high,
            "distance_pct": max(0.0, (high - current) / high * 100.0),
        }

    result = {
        "year_high": metric(year_high),
        "all_time_high": metric(all_time_high),
    }
    return result if any(result.values()) else None


def collect_digest_data(
    tickers: list[str],
    *,
    finnhub_key: str,
    indianapi_key: str,
    include_earnings: bool = False,
    include_price_ranges: bool = False,
    include_indian_media: bool = False,
) -> tuple[list[dict], int]:
    seen_stories: set[str] = set()
    sections: list[dict] = []
    total_stories = 0
    watched = list(tickers)

    raw_news: dict[str, list[dict]] = {}
    for ticker in tickers:
        market = market_of(ticker)
        section: dict = {
            "ticker": ticker,
            "display_symbol": display_symbol(ticker),
            "market": market,
            "exchange": market_badge(market) if market else "",
            "quote": None,
            "logo": None,
            "earnings_history": None,
            "upcoming_earnings": None,
            "price_ranges": None,
            "stories": [],
            "web_stories": [],
            "error": None,
        }

        news_loaded = False
        if market == "IN":
            try:
                section["quote"], raw_news[ticker] = fetch_quote_and_news(
                    ticker,
                    finnhub_key=finnhub_key,
                    indianapi_key=indianapi_key,
                )
            except requests.RequestException as exc:
                section["error"] = str(exc)
                raw_news[ticker] = []
            news_loaded = True
        else:
            try:
                section["quote"] = fetch_quote(
                    ticker,
                    finnhub_key=finnhub_key,
                    indianapi_key=indianapi_key,
                )
            except requests.RequestException:
                pass

        if include_price_ranges and section["quote"]:
            quote = section["quote"]
            current_price = quote.get("price")
            year_high = quote.get("year_high")
            all_time_high = None
            if market == "IN":
                try:
                    all_time_high = fetch_all_time_high(
                        ticker,
                        finnhub_key=finnhub_key,
                        indianapi_key=indianapi_key,
                    )
                except (requests.RequestException, TypeError, ValueError):
                    pass
            elif market == "US":
                try:
                    metrics = fetch_basic_financials(
                        ticker,
                        finnhub_key=finnhub_key,
                        indianapi_key=indianapi_key,
                    )
                    year_high = metrics.get("52WeekHigh")
                except (requests.RequestException, TypeError, ValueError):
                    pass
            section["price_ranges"] = build_price_ranges(
                current_price,
                year_high=year_high,
                all_time_high=all_time_high,
            )

        if market == "US" or include_indian_media:
            try:
                section["logo"] = fetch_company_logo(
                    ticker,
                    finnhub_key=finnhub_key,
                    indianapi_key=indianapi_key,
                )
            except requests.RequestException:
                pass

        if include_earnings:
            try:
                earnings = fetch_earnings_history(
                    ticker,
                    finnhub_key=finnhub_key,
                    indianapi_key=indianapi_key,
                    limit=4,
                )
                section["earnings_history"] = (
                    build_indian_earnings_history(earnings)
                    if market == "IN"
                    else build_earnings_history(earnings)
                )
            except (requests.RequestException, TypeError, ValueError):
                pass
            if market == "US":
                try:
                    section["upcoming_earnings"] = fetch_upcoming_earnings(
                        ticker,
                        finnhub_key=finnhub_key,
                        indianapi_key=indianapi_key,
                    )
                except (requests.RequestException, TypeError, ValueError):
                    pass

        if not news_loaded:
            try:
                raw_news[ticker] = fetch_news(
                    ticker,
                    finnhub_key=finnhub_key,
                    indianapi_key=indianapi_key,
                )
            except requests.RequestException as exc:
                section["error"] = str(exc)
                raw_news[ticker] = []

        sections.append(section)

    best_owner: dict[str, tuple[str, int]] = {}
    for ticker, news in raw_news.items():
        for item in news:
            key = story_dedupe_key(item)
            if not key:
                continue
            score = relevance_score(item, ticker, watched)
            previous = best_owner.get(key)
            if previous is None or score > previous[1]:
                best_owner[key] = (ticker, score)

    for section in sections:
        ticker = section["ticker"]
        news = raw_news.get(ticker, [])
        owned_news = []
        for item in news:
            key = story_dedupe_key(item)
            owner = best_owner.get(key)
            if owner and owner[0] != ticker and owner[1] >= MIN_RELEVANCE_SCORE:
                continue
            owned_news.append(item)

        if section["error"] and not owned_news:
            continue

        stories = select_stories(
            owned_news,
            seen_stories,
            ticker=ticker,
            watched_tickers=watched,
        )
        section["stories"] = stories
        section["web_stories"] = select_web_stories(
            owned_news,
            ticker=ticker,
            watched_tickers=watched,
        )
        total_stories += len(stories)

    return sections, total_stories


def abs_change_pct(section: dict) -> float:
    quote = section.get("quote")
    if not quote or quote.get("change_pct") is None:
        return 0.0
    return abs(quote["change_pct"])


def format_mover_label(ticker: str, change_pct: float | None) -> str:
    if change_pct is None:
        return ticker
    sign = "+" if change_pct >= 0 else ""
    return f"{ticker} {sign}{change_pct:.2f}%"


def prepare_email_layout(sections: list[dict]) -> dict:
    has_quotes = any(
        s.get("quote") and s["quote"].get("change_pct") is not None for s in sections
    )

    ranked = sorted(sections, key=abs_change_pct, reverse=True)

    if len(sections) == 1:
        hero = sections[0]
        compact = []
    elif has_quotes:
        hero = ranked[0]
        compact = ranked[1:]
    else:
        hero = None
        compact = list(sections)

    movers_bar: list[dict] = []
    gainers = losers = flat = 0

    for section in sections:
        quote = section.get("quote")
        change_pct = quote.get("change_pct") if quote else None
        price = quote.get("price") if quote else None

        if change_pct is None:
            flat += 1
            is_positive = None
        elif change_pct > 0:
            gainers += 1
            is_positive = True
        elif change_pct < 0:
            losers += 1
            is_positive = False
        else:
            flat += 1
            is_positive = None

        movers_bar.append(
            {
                "ticker": section["ticker"],
                "display_symbol": section.get("display_symbol") or section["ticker"],
                "market": section.get("market"),
                "exchange": section.get("exchange", ""),
                "price": price,
                "change_pct": change_pct,
                "is_positive": is_positive,
            }
        )

    movers_bar.sort(key=lambda m: abs(m["change_pct"] or 0), reverse=True)

    top_mover_label = None
    if hero:
        hero_change = hero.get("quote", {}).get("change_pct") if hero.get("quote") else None
        top_mover_label = format_mover_label(hero["ticker"], hero_change)

    return {
        "hero": hero,
        "compact": compact,
        "movers_bar": movers_bar,
        "market_summary": {"gainers": gainers, "losers": losers, "flat": flat},
        "top_mover_label": top_mover_label,
    }


def count_web_stories(sections: list[dict]) -> int:
    return sum(len(section.get("web_stories", [])) for section in sections)
