"""Jinja HTML rendering for web digest."""

from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape

from stock_news.config import (
    BREVO_API_KEY,
    BREVO_DOI_TEMPLATE_ID,
    BREVO_LIST_ID,
    DIGEST_HEADING,
    HEADLINES_PER_TICKER,
    SITE_URL,
    TEMPLATES_PATH,
)
from stock_news.digest import count_web_stories, prepare_email_layout
from stock_news.email import build_plain_text, build_email_content
from stock_news.markets import Market


def get_jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_PATH),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["format_number"] = lambda value: f"{value:,.0f}"
    return env


def subscribe_enabled() -> bool:
    return bool(BREVO_API_KEY and BREVO_LIST_ID and BREVO_DOI_TEMPLATE_ID)


def build_web_digest(
    sections: list[dict],
    tickers: list[str],
    *,
    fetched_at_label: str | None = None,
    fetched_at_iso: str | None = None,
    ai_summary: dict | None = None,
    subscribe_enabled_override: bool | None = None,
    progressive: bool = False,
    progressive_token: str | None = None,
) -> str:
    today_label = date.today().strftime("%d %b %Y")
    layout = prepare_email_layout(sections)
    layout["ai_summary"] = ai_summary
    web_story_count = count_web_stories(sections)
    env = get_jinja_env()
    template = env.get_template("web_digest.html")
    return template.render(
        date_label=today_label,
        ticker_count=len(tickers),
        story_count=web_story_count,
        site_url=SITE_URL,
        fetched_at_label=fetched_at_label,
        fetched_at_iso=fetched_at_iso,
        visible_story_count=HEADLINES_PER_TICKER,
        digest_heading=DIGEST_HEADING,
        subscribe_enabled=(
            subscribe_enabled()
            if subscribe_enabled_override is None
            else subscribe_enabled_override
        ),
        progressive=progressive,
        progressive_token=progressive_token,
        progressive_tickers=tickers if progressive else [],
        **layout,
    )


def build_web_section(section: dict) -> str:
    env = get_jinja_env()
    template = env.get_template("web_section.html")
    return template.render(section=section, visible_story_count=HEADLINES_PER_TICKER)


def build_email_digest(
    sections: list[dict],
    tickers: list[str],
    total_stories: int,
    session: str,
    market: Market = "US",
    *,
    digest_url: str | None = None,
    update_tickers_url: str | None = None,
    ai_summary: dict | None = None,
) -> tuple[str, str, str]:
    today_label = date.today().strftime("%d %b %Y")
    layout, email_heading, subject = build_email_content(
        sections,
        tickers,
        total_stories,
        session,
        ai_summary,
        market,
    )
    env = get_jinja_env()
    template = env.get_template("email_digest.html")
    html = template.render(
        date_label=today_label,
        ticker_count=len(tickers),
        story_count=total_stories,
        site_url=SITE_URL,
        email_heading=email_heading,
        digest_url=digest_url,
        update_tickers_url=update_tickers_url,
        **layout,
    )
    text = build_plain_text(
        layout,
        today_label,
        len(tickers),
        total_stories,
        email_heading=email_heading,
        digest_url=digest_url,
        update_tickers_url=update_tickers_url,
    )
    return html, text, subject


def build_digest_error(title: str, message: str, detail: str | None = None) -> str:
    env = get_jinja_env()
    template = env.get_template("digest_error.html")
    return template.render(
        title=title,
        message=message,
        detail=detail,
        site_url=SITE_URL,
        subscribe_enabled=subscribe_enabled(),
    )
