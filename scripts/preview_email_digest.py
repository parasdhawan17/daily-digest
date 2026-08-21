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

# Distinct Unsplash crops so each card looks different in the preview.
IMAGES = {
    "nvda_hero": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&h=400&fit=crop",
    "nvda_dc": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&h=400&fit=crop",
    "nvda_chip": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&h=400&fit=crop",
    "tsla_elon": "https://images.unsplash.com/photo-1560958089-b8a1929cea89?w=800&h=400&fit=crop",
    "tsla_factory": "https://images.unsplash.com/photo-1617788138017-80ad10651354?w=800&h=400&fit=crop",
    "meta_piggy": "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=800&h=400&fit=crop",
    "aapl_store": "https://images.unsplash.com/photo-1611186878181-cd9a39039094?w=800&h=400&fit=crop",
    "msft_cloud": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&h=400&fit=crop",
    "amzn_warehouse": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=800&h=400&fit=crop",
    "goog_ai": "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&h=400&fit=crop",
    "amd_cpu": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ed?w=800&h=400&fit=crop",
}


def story(
    *,
    headline: str,
    url: str,
    source: str,
    published_at: str,
    summary: str,
    image: str | None = None,
) -> dict:
    return {
        "headline": headline,
        "url": url,
        "source": source,
        "relative_time": "",
        "published_at": published_at,
        "summary": summary,
        "image": image,
    }


def main() -> None:
    sections = [
        {
            "ticker": "NVDA",
            "quote": {"price": 142.50, "change_pct": 4.82},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/NVDA.png",
            "hero_image": IMAGES["nvda_hero"],
            "stories": [
                story(
                    headline="Nvidia Blackwell shipments accelerate as hyperscalers lock in multi-year AI capacity deals",
                    url="https://example.com/nvda/blackwell-shipments",
                    source="Reuters",
                    published_at="21 Aug 2026, 11:18 AM UTC",
                    summary="Major cloud providers are front-loading orders for next-gen GPUs, with supply still tight through year-end. Analysts say data-center revenue could beat consensus again in FQ3.",
                    image=IMAGES["nvda_hero"],
                ),
                story(
                    headline="Data center demand keeps Nvidia supply chain at full tilt through 2026",
                    url="https://example.com/nvda/data-center-demand",
                    source="Bloomberg",
                    published_at="21 Aug 2026, 9:22 AM UTC",
                    summary="Co-packaged optics and HBM shortages remain bottlenecks, but channel checks suggest backlog visibility has extended to eight quarters for top-tier customers.",
                    image=IMAGES["nvda_dc"],
                ),
                story(
                    headline="Wall Street raises price targets after another round of AI infrastructure spend surveys",
                    url="https://example.com/nvda/price-targets",
                    source="CNBC",
                    published_at="21 Aug 2026, 7:05 AM UTC",
                    summary="Twelve firms lifted targets this week, citing stronger enterprise inference demand and improving gross margins on mature architectures.",
                    image=IMAGES["nvda_chip"],
                ),
            ],
            "error": None,
        },
        {
            "ticker": "TSLA",
            "quote": {"price": 345.13, "change_pct": -1.71},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/TSLA.png",
            "stories": [
                story(
                    headline="JPMorgan Says Tesla Is Confident of Scaling Cybercab Operations, Touts Future Models Based on Platform—FSD V15 a ‘Step-Change’ From Previous Versions",
                    url="https://example.com/tsla/jpm-cybercab",
                    source="Benzinga",
                    published_at="20 Aug 2026, 5:38 AM UTC",
                    summary="Analysts left the company’s AI day briefing constructive on robotaxi timelines, though they flagged execution risk around regulatory approvals and fleet utilization in dense urban markets.",
                    image=IMAGES["tsla_elon"],
                ),
            ],
            "error": None,
        },
        {
            "ticker": "META",
            "quote": {"price": 545.83, "change_pct": -0.04},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/META.png",
            "stories": [
                story(
                    headline="Meta Platforms: H2 2026 May Disappoint - Value Trap Risks Meet Rich Rebound Prospects",
                    url="https://example.com/meta/h2-outlook",
                    source="SeekingAlpha",
                    published_at="20 Aug 2026, 5:38 AM UTC",
                    summary="Meta has been able to generate rich advertising revenues of $59.36B in FQ2'26, accelerating from a year ago. Learn why META stock is a buy.",
                    image=IMAGES["meta_piggy"],
                ),
            ],
            "error": None,
        },
        {
            "ticker": "AAPL",
            "quote": {"price": 228.30, "change_pct": 1.18},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/AAPL.png",
            "stories": [
                story(
                    headline="Apple Intelligence rollout expands to more regions as developers adopt on-device APIs",
                    url="https://example.com/aapl/intelligence-rollout",
                    source="Bloomberg",
                    published_at="21 Aug 2026, 10:12 AM UTC",
                    summary="Services attach rates ticked higher in early markets where the feature set launched last quarter, supporting the bull case for margin expansion into the holiday cycle.",
                    image=IMAGES["aapl_store"],
                ),
            ],
            "error": None,
        },
        {
            "ticker": "MSFT",
            "quote": {"price": 415.20, "change_pct": 0.82},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/MSFT.png",
            "stories": [
                story(
                    headline="Microsoft Azure AI bookings remain ahead of plan, Copilot seat growth steady in enterprise",
                    url="https://example.com/msft/azure-ai",
                    source="Reuters",
                    published_at="21 Aug 2026, 8:45 AM UTC",
                    summary="Channel partners report lengthening contract durations for cloud commitments, with AI workloads increasingly bundled into existing EAs rather than sold standalone.",
                    image=IMAGES["msft_cloud"],
                ),
            ],
            "error": None,
        },
        {
            "ticker": "AMZN",
            "quote": {"price": 198.75, "change_pct": -0.92},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/AMZN.png",
            "stories": [
                story(
                    headline="Amazon Web Services wins large federal cloud contract, expanding AI-ready regions",
                    url="https://example.com/amzn/aws-federal",
                    source="Reuters",
                    published_at="21 Aug 2026, 6:30 AM UTC",
                    summary="The award adds to AWS’s public-sector backlog and could pull forward capex for sovereign cloud capacity in two U.S. regions over the next eighteen months.",
                    image=IMAGES["amzn_warehouse"],
                ),
            ],
            "error": None,
        },
        {
            "ticker": "GOOGL",
            "quote": {"price": 178.20, "change_pct": -0.35},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/GOOGL.png",
            "stories": [
                story(
                    headline="Alphabet search share holds steady as Gemini integrations roll out across core products",
                    url="https://example.com/googl/gemini-search",
                    source="Bloomberg",
                    published_at="21 Aug 2026, 5:15 AM UTC",
                    summary="Early data suggests query monetization is stable despite AI overviews, though investors remain focused on capex intensity relative to peers.",
                    image=IMAGES["goog_ai"],
                ),
            ],
            "error": None,
        },
        {
            "ticker": "AMD",
            "quote": {"price": 162.40, "change_pct": 0.0},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/AMD.png",
            "stories": [
                story(
                    headline="AMD MI350 ramp on track, but investors await clearer hyperscaler mix shift",
                    url="https://example.com/amd/mi350-ramp",
                    source="Barron's",
                    published_at="21 Aug 2026, 4:02 AM UTC",
                    summary="Management reiterated guidance on data-center GPU share gains, while noting client CPU demand remains seasonally soft ahead of back-to-school.",
                    image=IMAGES["amd_cpu"],
                ),
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
