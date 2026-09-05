"""Pre-redesign plain-text presentation; shared delivery remains in email.py."""

from stock_news.config import SITE_URL
from stock_news.markets import display_symbol

def footer_text(
    ticker_count: int,
    story_count: int,
    *,
    digest_url: str | None = None,
    update_tickers_url: str | None = None,
) -> str:
    line = f"{ticker_count} tickers · {story_count} stories · Tickr Digest"
    if digest_url:
        line += f"\nRead full digest: {digest_url}"
    if update_tickers_url:
        line += f"\nUpdate your tickers: {update_tickers_url}"
    elif SITE_URL:
        line += f"\nRead full digest: {SITE_URL}/"
        line += f"\nUpdate your tickers: {SITE_URL}/#update-tickers"
    return line


def format_section_plain_text(
    section: dict,
    *,
    compact: bool = False,
    ai_summary_text: str | None = None,
) -> list[str]:
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

    if ai_summary_text:
        lines.append(f"AI brief: {ai_summary_text}")
        lines.append("")

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
    title = email_heading or f"Tickr Digest · {date_label}"
    lines = [
        title,
        f"{date_label} · {ticker_count} tickers · {story_count} stories",
        f"{summary['gainers']} up · {summary['losers']} down · {summary['flat']} flat",
        "",
    ]

    ai_summary = layout.get("ai_summary")
    if ai_summary:
        lines.append("=== AI BRIEFING ===")
        lines.append(ai_summary["market_context"])
        lines.append("")
        for ticker, summary_text in ai_summary.get("ticker_summaries", {}).items():
            lines.append(f"{display_symbol(ticker)}: {summary_text}")
        lines.append("")

    if layout["top_mover_label"]:
        lines.append(f"Today's biggest move: {layout['top_mover_label']}")
        lines.append("")

    if layout["hero"]:
        lines.append("=== BIGGEST MOVER ===")
        hero_ticker = layout["hero"]["ticker"]
        lines.extend(
            format_section_plain_text(
                layout["hero"],
                compact=False,
                ai_summary_text=(ai_summary or {}).get("ticker_summaries", {}).get(hero_ticker),
            )
        )

    for section in layout["compact"]:
        lines.extend(
            format_section_plain_text(
                section,
                compact=True,
                ai_summary_text=(ai_summary or {}).get("ticker_summaries", {}).get(
                    section["ticker"]
                ),
            )
        )

    lines.append(
        footer_text(
            ticker_count,
            story_count,
            digest_url=digest_url,
            update_tickers_url=update_tickers_url,
        )
    )
    return "\n".join(lines)


