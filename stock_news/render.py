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


def get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_PATH),
        autoescape=select_autoescape(["html"]),
    )


def subscribe_enabled() -> bool:
    return bool(BREVO_API_KEY and BREVO_LIST_ID and BREVO_DOI_TEMPLATE_ID)


def build_web_digest(
    sections: list[dict],
    tickers: list[str],
    *,
    fetched_at_label: str | None = None,
) -> str:
    today_label = date.today().strftime("%d %b %Y")
    layout = prepare_email_layout(sections)
    web_story_count = count_web_stories(sections)
    env = get_jinja_env()
    template = env.get_template("web_digest.html")
    return template.render(
        date_label=today_label,
        ticker_count=len(tickers),
        story_count=web_story_count,
        site_url=SITE_URL,
        fetched_at_label=fetched_at_label,
        visible_story_count=HEADLINES_PER_TICKER,
        digest_heading=DIGEST_HEADING,
        subscribe_enabled=subscribe_enabled(),
        **layout,
    )


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
