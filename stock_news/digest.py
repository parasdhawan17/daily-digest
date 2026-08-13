"""Collect Finnhub data and prepare digest layout."""

import requests

from stock_news.config import HEADLINES_PER_TICKER, MIN_RELEVANCE_SCORE
from stock_news.finnhub import (
    fetch_company_logo,
    fetch_news,
    fetch_quote,
    story_dedupe_key,
)
from stock_news.relevance import relevance_score, select_stories, select_web_stories


def filter_sections(sections: list[dict], tickers: list[str]) -> list[dict]:
    ticker_set = set(tickers)
    return [section for section in sections if section["ticker"] in ticker_set]


def collect_digest_data(tickers: list[str], api_key: str) -> tuple[list[dict], int]:
    seen_stories: set[str] = set()
    sections: list[dict] = []
    total_stories = 0
    watched = list(tickers)

    raw_news: dict[str, list[dict]] = {}
    for ticker in tickers:
        section: dict = {
            "ticker": ticker,
            "quote": None,
            "logo": None,
            "hero_image": None,
            "stories": [],
            "web_stories": [],
            "error": None,
        }

        try:
            section["quote"] = fetch_quote(ticker, api_key)
        except requests.RequestException:
            pass

        try:
            section["logo"] = fetch_company_logo(ticker, api_key)
        except requests.RequestException:
            pass

        try:
            raw_news[ticker] = fetch_news(ticker, api_key)
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
        section["hero_image"] = next((story["image"] for story in stories if story["image"]), None)
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
