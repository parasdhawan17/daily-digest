#!/usr/bin/env python3
"""Build public/preview-digest.html for local UI testing."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SITE_URL", "http://localhost:8765")
os.environ.setdefault(
    "BREVO_SUBSCRIBE_FORM_URL",
    "https://c45d1150.sibforms.com/serve/MUIFAHIL1jH-DeVrUnpoo9864EFxz9zv2_ZPiO5KF3s6v4dRsO78MCqs3Px8F3YEkQEleXXhoo3-ru-TV0wfGKmx-2GDoycH5AKn6zALH_5j980Isx-qMT0_GjO7sEv1dSME02tsPJpnG84htHPDroxqPtqY8u1Wt0NWE-MguymSMwInpWKhcLGiRmaKzN0-Y1ZM6iMYpio_ixYtWw==",
)

from stock_news.render import build_web_digest

# Working stock-themed placeholder (Unsplash photo IDs must be valid — 404s show as broken images).
STOCK_IMAGE = "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&h=400&fit=crop"


def story(i: int, ticker: str, headline: str, source: str = "Reuters", mins: int = 2, with_image: bool = True) -> dict:
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
            "quote": {"price": 142.50, "change_pct": 2.14},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/NVDA.png",
            "web_stories": [
                story(0, "NVDA", "Nvidia announces next-gen chip roadmap ahead of earnings"),
                story(1, "NVDA", "Data center demand keeps Nvidia supply chain at full tilt", "Bloomberg", 3),
                story(2, "NVDA", "Wall Street raises price targets after AI infrastructure spend", "CNBC", 4, False),
                story(3, "NVDA", "Partners line up for new accelerator platform launch", "Reuters", 5),
                story(4, "NVDA", "Semiconductor peers rally on Nvidia guidance optimism", "MarketWatch", 6, False),
            ],
            "error": None,
        },
        {
            "ticker": "AAPL",
            "quote": {"price": 228.30, "change_pct": 1.18},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/AAPL.png",
            "web_stories": [
                story(0, "AAPL", "Apple expands AI features across iOS developer preview", "Bloomberg", 2),
                story(1, "AAPL", "Services revenue momentum offsets hardware cycle concerns", "Reuters", 4, False),
            ],
            "error": None,
        },
        {
            "ticker": "MSFT",
            "quote": {"price": 415.20, "change_pct": 0.82},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/MSFT.png",
            "web_stories": [
                story(0, "MSFT", "Microsoft cloud growth stays resilient in enterprise spend survey", "Reuters", 1),
            ],
            "error": None,
        },
        {
            "ticker": "TSLA",
            "quote": {"price": 248.90, "change_pct": -0.64},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/TSLA.png",
            "web_stories": [
                story(0, "TSLA", "Tesla delivery estimates shift as competition intensifies", "Bloomberg", 3),
                story(1, "TSLA", "Analysts debate margin outlook after recent price adjustments", "CNBC", 5, False),
            ],
            "error": None,
        },
    ]

    tickers = [section["ticker"] for section in sections]
    html = build_web_digest(
        sections,
        tickers,
        fetched_at_label="Fetched at 9:15 AM ET · Aug 15, 2026",
    )
    out = ROOT / "public" / "preview-digest.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out} ({len(html)} bytes)")
    print("Open http://localhost:8765/preview-digest.html")


if __name__ == "__main__":
    main()
