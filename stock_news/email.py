"""Email digest subject lines, plain text, and session helpers."""

from datetime import date, datetime, timedelta, timezone

from stock_news.config import (
    DIGEST_HEADING,
    EMAIL_SCHEDULE_MAX_AHEAD_MINUTES,
    ET_ZONE,
    HEADLINE_SNIPPET_LEN,
    IN_MARKET_CLOSE_IST,
    IN_MARKET_OPEN_IST,
    IN_POST_CLOSE_SEND_IST,
    IN_PRE_OPEN_SEND_IST,
    IST_ZONE,
    MARKET_CLOSE_ET,
    MARKET_OPEN_ET,
    MAX_SUBJECT_HEADLINES,
    MAX_SUBJECT_MOVERS,
    POST_CLOSE_SEND_ET,
    PRE_OPEN_SEND_ET,
    SITE_URL,
    SUBJECT_MAX_LEN,
)
from stock_news.digest import prepare_email_layout
from stock_news.markets import Market, display_symbol

CRON_WINDOWS: tuple[tuple[Market, str, int, int], ...] = (
    ("IN", "pre_open", 3, 45),
    ("IN", "post_close", 10, 15),
    ("US", "pre_open", 13, 0),
    ("US", "post_close", 20, 0),
)


def union_tickers(subscribers: list[dict]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for subscriber in subscribers:
        for ticker in subscriber.get("tickers", []):
            if ticker not in seen:
                seen.add(ticker)
                result.append(ticker)
    return result


def count_email_stories(sections: list[dict]) -> int:
    return sum(len(section.get("stories", [])) for section in sections)


def digest_session(
    market: Market = "US",
    now: datetime | None = None,
    override: str = "auto",
) -> str:
    """Return 'pre_open' or 'post_close' for a market clock or explicit override."""
    if override in ("pre_open", "post_close"):
        return override

    zone = IST_ZONE if market == "IN" else ET_ZONE
    open_clock = IN_MARKET_OPEN_IST if market == "IN" else MARKET_OPEN_ET
    close_clock = IN_MARKET_CLOSE_IST if market == "IN" else MARKET_CLOSE_ET

    current = (now or datetime.now(zone)).astimezone(zone)
    local_time = current.time()
    if local_time < open_clock:
        return "pre_open"
    if local_time >= close_clock:
        return "post_close"
    return "pre_open" if current.hour < 12 else "post_close"


def scheduled_send_at_iso(
    session: str,
    market: Market = "US",
    now: datetime | None = None,
) -> str | None:
    """ISO-8601 time for Brevo scheduledAt, or None to send immediately."""
    zone = IST_ZONE if market == "IN" else ET_ZONE
    if market == "IN":
        send_clock = IN_PRE_OPEN_SEND_IST if session == "pre_open" else IN_POST_CLOSE_SEND_IST
    else:
        send_clock = PRE_OPEN_SEND_ET if session == "pre_open" else POST_CLOSE_SEND_ET

    current = (now or datetime.now(zone)).astimezone(zone)
    target = current.replace(
        hour=send_clock.hour,
        minute=send_clock.minute,
        second=0,
        microsecond=0,
    )
    if target <= current:
        return None
    if (target - current) > timedelta(minutes=EMAIL_SCHEDULE_MAX_AHEAD_MINUTES):
        return None
    return target.isoformat()


def cron_sessions(now: datetime | None = None) -> list[tuple[Market, str]]:
    """Return active (market, session) pairs for the current UTC cron window."""
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    active: list[tuple[Market, str]] = []
    for market, session, hour, minute in CRON_WINDOWS:
        delta = abs((current.hour * 60 + current.minute) - (hour * 60 + minute))
        if delta <= EMAIL_SCHEDULE_MAX_AHEAD_MINUTES:
            active.append((market, session))
    return active


def truncate_subject_snippet(text: str, max_len: int = HEADLINE_SNIPPET_LEN) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 1].rstrip(" ,;:-")
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0].rstrip(" ,;:-")
    return (cut or text[: max_len - 1].rstrip()) + "…"


def mover_subject_chip(mover: dict) -> str | None:
    change_pct = mover.get("change_pct")
    if change_pct is None:
        return None
    if change_pct > 0:
        emoji = "📈"
    elif change_pct < 0:
        emoji = "📉"
    else:
        emoji = "➡️"
    return f"{emoji} {mover.get('display_symbol') or display_symbol(mover['ticker'])} {change_pct:+.1f}%"


def join_subject_chips(chips: list[str], *, prefix: str = "") -> str | None:
    if not chips:
        return None
    while chips:
        body = " · ".join(chips)
        subject = f"{prefix}{body}" if prefix else body
        if len(subject) <= SUBJECT_MAX_LEN:
            return subject
        chips = chips[:-1]
    return None


def format_pre_open_subject(layout: dict, date_label: str) -> str:
    sections: list[dict] = []
    hero = layout.get("hero")
    if hero:
        sections.append(hero)
    sections.extend(layout.get("compact") or [])

    chips: list[str] = []
    for section in sections:
        stories = section.get("stories") or []
        if not stories:
            continue
        headline = (stories[0].get("headline") or "").strip()
        if not headline:
            continue
        snippet = truncate_subject_snippet(headline)
        chips.append(f"{display_symbol(section['ticker'])} · {snippet}")
        if len(chips) >= MAX_SUBJECT_HEADLINES:
            break

    subject = join_subject_chips(chips, prefix="💡 ")
    return subject or f"📊 Stock News · {date_label}"


def format_post_close_subject(layout: dict, date_label: str) -> str:
    chips: list[str] = []
    for mover in layout.get("movers_bar") or []:
        chip = mover_subject_chip(mover)
        if not chip:
            continue
        chips.append(chip)
        if len(chips) >= MAX_SUBJECT_MOVERS:
            break

    subject = join_subject_chips(chips)
    return subject or f"📊 Stock News · {date_label}"


def format_email_subject(layout: dict, date_label: str, session: str) -> str:
    if session == "pre_open":
        return format_pre_open_subject(layout, date_label)
    return format_post_close_subject(layout, date_label)


def format_email_heading(layout: dict) -> str:
    hero = layout.get("hero")
    if not hero:
        return DIGEST_HEADING
    ticker = display_symbol(hero["ticker"])
    quote = hero.get("quote")
    if not quote or quote.get("change_pct") is None:
        return DIGEST_HEADING
    change_pct = quote["change_pct"]
    if change_pct > 0:
        return f"{ticker} moved high"
    if change_pct < 0:
        return f"{ticker} moved low"
    return f"{ticker} held steady"


def footer_text(
    ticker_count: int,
    story_count: int,
    *,
    digest_url: str | None = None,
    update_tickers_url: str | None = None,
) -> str:
    line = f"{ticker_count} tickers · {story_count} stories · Stock News"
    if digest_url:
        line += f"\nRead full digest: {digest_url}"
    if update_tickers_url:
        line += f"\nUpdate your tickers: {update_tickers_url}"
    elif SITE_URL:
        line += f"\nRead full digest: {SITE_URL}/"
        line += f"\nUpdate your tickers: {SITE_URL}/#update-tickers"
    return line


def format_section_plain_text(section: dict, *, compact: bool = False) -> list[str]:
    lines: list[str] = []
    ticker_line = display_symbol(section["ticker"])
    if section["quote"]:
        quote = section["quote"]
        currency = "₹" if section.get("market") == "IN" else "$"
        ticker_line += f"  {currency}{quote['price']:.2f}"
        if quote["change_pct"] is not None:
            sign = "+" if quote["change_pct"] >= 0 else ""
            ticker_line += f"  {sign}{quote['change_pct']:.2f}%"
    lines.append(ticker_line)
    lines.append("-" * len(ticker_line))

    if section["error"]:
        lines.append(f"Could not fetch news for {section['ticker']}.")
    elif not section["stories"]:
        lines.append(f"No major news for {section['ticker']} today.")
    elif compact:
        story = section["stories"][0]
        lines.append(f"• {story['headline']}")
        if story["url"]:
            lines.append(f"  {story['url']}")
    else:
        for index, story in enumerate(section["stories"], start=1):
            lines.append(f"{index}. {story['headline']}")
            if story["summary"]:
                lines.append(f"   {story['summary']}")
            meta = story["source"]
            story_time = story.get("published_at") or story.get("relative_time")
            if story_time:
                meta = f"{meta} · {story_time}"
            lines.append(f"   {meta}")
            if story["url"]:
                lines.append(f"   {story['url']}")
            lines.append("")

    lines.append("")
    return lines


def build_plain_text(
    layout: dict,
    date_label: str,
    ticker_count: int,
    story_count: int,
    *,
    email_heading: str | None = None,
    digest_url: str | None = None,
    update_tickers_url: str | None = None,
) -> str:
    summary = layout["market_summary"]
    title = email_heading or f"Stock News · {date_label}"
    lines = [
        title,
        f"{date_label} · {ticker_count} tickers · {story_count} stories",
        f"{summary['gainers']} up · {summary['losers']} down · {summary['flat']} flat",
        "",
    ]

    if layout["top_mover_label"]:
        lines.append(f"Today's biggest move: {layout['top_mover_label']}")
        lines.append("")

    if layout["hero"]:
        lines.append("=== BIGGEST MOVER ===")
        lines.extend(format_section_plain_text(layout["hero"], compact=False))

    for section in layout["compact"]:
        lines.extend(format_section_plain_text(section, compact=True))

    lines.append(
        footer_text(
            ticker_count,
            story_count,
            digest_url=digest_url,
            update_tickers_url=update_tickers_url,
        )
    )
    return "\n".join(lines)


def build_email_content(
    sections: list[dict],
    tickers: list[str],
    total_stories: int,
    session: str,
) -> tuple[dict, str, str]:
    """Return layout, email_heading, and subject for an email digest."""
    layout = prepare_email_layout(sections)
    today_label = date.today().strftime("%d %b %Y")
    email_heading = format_email_heading(layout)
    subject = format_email_subject(layout, today_label, session)
    return layout, email_heading, subject
