#!/usr/bin/env python3
"""Build public/preview-email-digest.html for local email template testing."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SITE_URL", "http://localhost:8765")

from stock_news.email import count_email_stories
from stock_news.render import build_email_digest

STOCK_IMAGE = "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&h=400&fit=crop"


def story(
    i: int,
    ticker: str,
    headline: str,
    source: str = "Reuters",
    mins: int = 2,
    *,
    with_image: bool = True,
) -> dict:
    img = f"{STOCK_IMAGE}&sig={ticker}{i}" if with_image else None
    return {
        "headline": headline,
        "url": f"https://example.com/{ticker.lower()}/{i}",
        "source": source,
        "relative_time": f"{mins + i}h ago",
        "summary": "Analysts weigh supply constraints, guidance, and sector rotation as investors reposition ahead of the next earnings cycle.",
        "image": img,
    }


def main() -> None:
    sections = [
        {
            "ticker": "NVDA",
            "quote": {"price": 142.50, "change_pct": 4.82},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/NVDA.png",
            "hero_image": f"{STOCK_IMAGE}&sig=nvda-hero",
            "stories": [
                story(0, "NVDA", "Nvidia announces next-gen chip roadmap ahead of earnings"),
                story(1, "NVDA", "Data center demand keeps Nvidia supply chain at full tilt", "Bloomberg", 3),
                story(2, "NVDA", "Wall Street raises price targets after AI infrastructure spend", "CNBC", 4, with_image=False),
            ],
            "error": None,
        },
        {
            "ticker": "AAPL",
            "quote": {"price": 228.30, "change_pct": 1.18},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/AAPL.png",
            "stories": [
                story(0, "AAPL", "Apple expands AI features across iOS developer preview", "Bloomberg", 2),
            ],
            "error": None,
        },
        {
            "ticker": "MSFT",
            "quote": {"price": 415.20, "change_pct": 0.82},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/MSFT.png",
            "stories": [
                story(0, "MSFT", "Microsoft cloud growth stays resilient in enterprise spend survey", "Reuters", 1),
            ],
            "error": None,
        },
        {
            "ticker": "TSLA",
            "quote": {"price": 248.90, "change_pct": -2.64},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/TSLA.png",
            "stories": [
                story(0, "TSLA", "Tesla delivery estimates shift as competition intensifies", "Bloomberg", 3),
            ],
            "error": None,
        },
        {
            "ticker": "META",
            "quote": {"price": 512.40, "change_pct": -1.45},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/META.png",
            "stories": [
                story(0, "META", "Meta ad revenue beats estimates on Reels monetization", "CNBC", 2),
            ],
            "error": None,
        },
        {
            "ticker": "AMZN",
            "quote": {"price": 198.75, "change_pct": -0.92},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/AMZN.png",
            "stories": [
                story(0, "AMZN", "Amazon Web Services wins large federal cloud contract", "Reuters", 4),
            ],
            "error": None,
        },
        {
            "ticker": "GOOGL",
            "quote": {"price": 178.20, "change_pct": -0.35},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/GOOGL.png",
            "stories": [
                story(0, "GOOGL", "Alphabet search share holds steady amid AI chat competition", "Bloomberg", 5),
            ],
            "error": None,
        },
    ]

    tickers = [section["ticker"] for section in sections]
    total_stories = count_email_stories(sections)
    html, text, subject = build_email_digest(
        sections,
        tickers,
        total_stories,
        session="post_close",
        digest_url="http://localhost:8765/digest?t=preview-token",
        update_tickers_url="http://localhost:8765/#update-tickers",
    )

    out = ROOT / "public" / "preview-email-digest.html"
    out.write_text(html, encoding="utf-8")
    text_out = ROOT / "public" / "preview-email-digest.txt"
    text_out.write_text(text, encoding="utf-8")

    print(f"Wrote {out} ({len(html)} bytes)")
    print(f"Wrote {text_out} ({len(text)} bytes)")
    print(f"Subject: {subject}")
    print("Open http://localhost:8765/preview-email-digest.html")


if __name__ == "__main__":
    main()
