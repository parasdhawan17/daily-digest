"""Ticker aliases and story relevance scoring."""

import json
import re

from stock_news.config import (
    HEADLINE_ALIAS_POINTS,
    MIN_RELEVANCE_SCORE,
    MIN_STORIES_PER_TICKER,
    RIVAL_PENALTY,
    SUMMARY_ALIAS_POINTS,
    TICKER_ALIASES_PATH,
    TICKER_SYMBOL_BONUS,
)
from stock_news.markets import display_symbol, normalize_ticker
from stock_news.finnhub import story_dedupe_key, sanitize_article_image
from stock_news.formatting import excerpt_summary, format_full_datetime, format_relative_time

_TICKER_ALIASES_CACHE: dict[str, list[str]] | None = None
_ALIAS_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def load_ticker_aliases() -> dict[str, list[str]]:
    global _TICKER_ALIASES_CACHE
    if _TICKER_ALIASES_CACHE is not None:
        return _TICKER_ALIASES_CACHE

    if not TICKER_ALIASES_PATH.is_file():
        _TICKER_ALIASES_CACHE = {}
        return _TICKER_ALIASES_CACHE

    data = json.loads(TICKER_ALIASES_PATH.read_text(encoding="utf-8"))
    raw = data.get("aliases", data)
    aliases: dict[str, list[str]] = {}
    for ticker, values in raw.items():
        key = str(ticker).strip().upper()
        if not key:
            continue
        seen: set[str] = set()
        cleaned: list[str] = []
        for value in values or []:
            alias = str(value).strip()
            if not alias:
                continue
            lowered = alias.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(alias)
        if cleaned:
            aliases[key] = cleaned
    _TICKER_ALIASES_CACHE = aliases
    return _TICKER_ALIASES_CACHE


def aliases_for(ticker: str) -> list[str]:
    ticker = ticker.strip().upper()
    aliases = load_ticker_aliases().get(ticker, [])
    if ticker and ticker.lower() not in {a.lower() for a in aliases}:
        return [ticker, *aliases]
    return aliases or ([ticker] if ticker else [])


def _alias_pattern(alias: str) -> re.Pattern[str]:
    cached = _ALIAS_PATTERN_CACHE.get(alias)
    if cached is not None:
        return cached
    escaped = re.escape(alias)
    pattern = re.compile(rf"(?<![A-Za-z0-9])\$?{escaped}(?![A-Za-z0-9])", re.IGNORECASE)
    _ALIAS_PATTERN_CACHE[alias] = pattern
    return pattern


def whole_word_match(alias: str, text: str) -> bool:
    if not alias or not text:
        return False
    return _alias_pattern(alias).search(text) is not None


def relevance_score(
    item: dict,
    ticker: str,
    watched_tickers: list[str] | set[str] | None = None,
) -> int:
    headline = (item.get("headline") or "").strip()
    summary = (item.get("summary") or "").strip()
    if not headline and not summary:
        return 0

    score = 0
    headline_hits = 0
    summary_hits = 0
    for alias in aliases_for(ticker):
        if whole_word_match(alias, headline):
            headline_hits += 1
        elif whole_word_match(alias, summary):
            summary_hits += 1

    score += min(headline_hits, 2) * HEADLINE_ALIAS_POINTS
    score += min(summary_hits, 2) * SUMMARY_ALIAS_POINTS

    if whole_word_match(ticker, headline) or whole_word_match(display_symbol(ticker), headline):
        score += TICKER_SYMBOL_BONUS

    own_hit = score > 0
    watched = {t.strip().upper() for t in (watched_tickers or []) if t}
    watched.discard(ticker.strip().upper())
    if not own_hit and watched:
        for other in watched:
            if any(whole_word_match(alias, headline) for alias in aliases_for(other)):
                score -= RIVAL_PENALTY
                break

    return score


def parse_tickers(raw: str | list | tuple | None) -> list[str]:
    if raw is None:
        return []

    if isinstance(raw, (list, tuple)):
        parts = [str(item) for item in raw]
    else:
        text = str(raw).strip()
        if not text:
            return []
        parts = re.split(r"[,;\s]+", text)

    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        normalized = normalize_ticker(part)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _build_story_dict(
    item: dict,
    score: int,
    *,
    excerpt: bool,
    relevance_fallback: bool,
) -> dict:
    summary = item.get("summary", "").strip()
    return {
        "headline": item.get("headline", "No headline").strip(),
        "summary": excerpt_summary(summary) if excerpt and summary else summary,
        "image": sanitize_article_image(item.get("image")),
        "url": item.get("url", "").strip(),
        "source": item.get("source", "").strip() or "News",
        "relative_time": format_relative_time(item.get("datetime")),
        "published_at": format_full_datetime(item.get("datetime")),
        "relevance_score": score,
        "relevance_fallback": relevance_fallback,
    }


def select_stories(
    news: list[dict],
    seen_stories: set[str],
    limit: int = 3,
    *,
    excerpt: bool = True,
    ticker: str | None = None,
    watched_tickers: list[str] | set[str] | None = None,
    min_score: int = MIN_RELEVANCE_SCORE,
    min_stories: int = MIN_STORIES_PER_TICKER,
    allow_fallback: bool = True,
) -> list[dict]:
    ranked: list[tuple[int, int, dict]] = []
    for index, item in enumerate(news):
        key = story_dedupe_key(item)
        if not key or key in seen_stories:
            continue

        score = 0
        if ticker:
            score = relevance_score(item, ticker, watched_tickers)
        ranked.append((score, index, item))

    ranked.sort(key=lambda row: (-row[0], row[1]))

    stories: list[dict] = []
    selected_keys: set[str] = set()

    def take_from(
        pool: list[tuple[int, int, dict]],
        target_count: int,
        *,
        fallback: bool,
    ) -> None:
        for score, _index, item in pool:
            if len(stories) >= target_count:
                return
            key = story_dedupe_key(item)
            if not key or key in seen_stories or key in selected_keys:
                continue
            selected_keys.add(key)
            seen_stories.add(key)
            stories.append(
                _build_story_dict(
                    item,
                    score,
                    excerpt=excerpt,
                    relevance_fallback=fallback,
                )
            )

    strong = [(score, index, item) for score, index, item in ranked if score >= min_score]
    take_from(strong, limit, fallback=False)

    if allow_fallback and len(stories) < min_stories:
        take_from(ranked, min_stories, fallback=True)

    return stories


def select_web_stories(
    news: list[dict],
    limit: int = 10,
    *,
    ticker: str | None = None,
    watched_tickers: list[str] | set[str] | None = None,
) -> list[dict]:
    from stock_news.config import WEB_HEADLINES_PER_TICKER

    return select_stories(
        news,
        set(),
        limit=limit or WEB_HEADLINES_PER_TICKER,
        excerpt=False,
        ticker=ticker,
        watched_tickers=watched_tickers,
    )
