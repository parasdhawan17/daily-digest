#!/usr/bin/env python3
"""Build public/preview-digest.html for local UI testing."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SITE_URL", "http://localhost:8765")

from stock_news.digest import build_earnings_history, build_indian_earnings_history
from stock_news.design import resolve_design
from stock_news.render import build_web_digest
from stock_news.financial_health import build_financial_health

# Working stock-themed placeholder (Unsplash photo IDs must be valid — 404s show as broken images).
STOCK_IMAGE = "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&h=400&fit=crop"


def sample_financial_health():
    """Illustrative statement-shaped data for the local visual preview."""
    statements = []
    for year, revenue, operating, profit, debt, cash, ocf, capex in (
        (2022, 191754, 48451, 38327, 7818, 12488, 39949, -2995),
        (2023, 225458, 54235, 42147, 7688, 7123, 41965, -3100),
        (2024, 240893, 58360, 45908, 8021, 9007, 44338, -2674),
        (2025, 255324, 62183, 48553, 9392, 8331, 48908, -5000),
        (2026, 267021, 62632, 49210, 11409, 6405, 52094, -4700),
    ):
        fields = {
            "INC": {"TotalRevenue": revenue, "OperatingIncome": operating, "NetIncome": profit,
                    "DilutedEPSExcludingExtraOrdItems": profit / 362, "periodLength": 12},
            "BAL": {"Cash": cash / 2, "CashEquivalents": cash / 2, "TotalDebt": debt, "TotalEquity": 107240},
            "CAS": {"CashfromOperatingActivities": ocf, "CapitalExpenditures": capex},
        }
        statements.append({"Type": "Annual", "FiscalYear": str(year), "EndDate": f"{year}-03-31",
                           "stockFinancialMap": {group: [{"key": key, "value": str(value)} for key, value in values.items()]
                                                 for group, values in fields.items()}})
    return build_financial_health({"industry": "Software & Programming", "financials": statements,
        "keyMetrics": {"mgmtEffectiveness": [{"key": "returnOnAverageEquityTrailing12Month", "value": "47.99"},
                                              {"key": "returnOnAverageAssetsTrailing12Month", "value": "28.55"}],
                       "persharedata": [{"key": "cashFlowPerShareTrailing12Month", "value": "153.38"}]}})


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


def earnings_quarter(period: str, year: int, quarter: int, actual: float, estimate: float) -> dict:
    surprise_pct = (actual - estimate) / abs(estimate) * 100 if estimate else 0.0
    result = "beat" if surprise_pct > 0 else "miss" if surprise_pct < 0 else "inline"
    return {
        "period": period,
        "fiscal_year": year,
        "fiscal_quarter": quarter,
        "label": f"Q{quarter} FY{str(year)[-2:]}",
        "actual": actual,
        "estimate": estimate,
        "surprise": actual - estimate,
        "surprise_pct": surprise_pct,
        "result": result,
    }


def upcoming_earnings(date_label: str, hour: str, eps: float, revenue: float) -> dict:
    return {
        "date": "2026-09-15",
        "date_label": date_label,
        "hour": hour,
        "eps_estimate": eps,
        "eps_actual": None,
        "revenue_estimate": revenue,
        "revenue_actual": None,
    }


def reported_quarter(
    period: str,
    period_label: str,
    label: str,
    eps: float,
    sales: float,
    net_profit: float,
    opm_pct: float,
) -> dict:
    return {
        "mode": "reported",
        "period": period,
        "period_label": period_label,
        "label": label,
        "actual": eps,
        "sales": sales,
        "net_profit": net_profit,
        "opm_pct": opm_pct,
    }


def main() -> None:
    sections = [
        {
            "ticker": "US:NVDA",
            "display_symbol": "NVDA",
            "market": "US",
            "exchange": "US",
            "quote": {"price": 142.50, "change_pct": 2.14},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/NVDA.png",
            "earnings_history": build_earnings_history(
                [
                    earnings_quarter("2025-07-31", 2026, 2, 1.05, 1.01),
                    earnings_quarter("2025-10-31", 2026, 3, 1.30, 1.26),
                    earnings_quarter("2026-01-31", 2026, 4, 1.42, 1.45),
                    earnings_quarter("2026-04-30", 2027, 1, 1.68, 1.61),
                ]
            ),
            "upcoming_earnings": upcoming_earnings("15 Sep 2026", "amc", 1.68, 52000000000),
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
            "ticker": "IN:RELIANCE",
            "display_symbol": "RELIANCE",
            "market": "IN",
            "exchange": "NSE",
            "quote": {"price": 2856.40, "change_pct": -0.42},
            "price_ranges": {
                "year_high": {"value": 3217.60, "distance_pct": 11.23},
                "all_time_high": {"value": 3217.60, "distance_pct": 11.23},
            },
            "logo": None,
            "earnings_history": build_indian_earnings_history(
                [
                    reported_quarter("2025-09-01", "Sep 2025", "Q2 FY26", 27.14, 258407, 18450, 17.1),
                    reported_quarter("2025-12-01", "Dec 2025", "Q3 FY26", 29.32, 269496, 20185, 17.6),
                    reported_quarter("2026-03-01", "Mar 2026", "Q4 FY26", 31.08, 274732, 21930, 18.0),
                    reported_quarter("2026-06-01", "Jun 2026", "Q1 FY27", 32.44, 281109, 22840, 18.3),
                ]
            ),
            "upcoming_earnings": None,
            "web_stories": [
                story(0, "RELIANCE", "Reliance Industries reports steady refining margins", "Economic Times", 2),
                story(1, "RELIANCE", "Jio subscriber growth remains strong in quarterly update", "Mint", 4, False),
            ],
            "error": None,
        },
        {
            "ticker": "US:AAPL",
            "display_symbol": "AAPL",
            "market": "US",
            "exchange": "US",
            "quote": {"price": 228.30, "change_pct": 1.18},
            "logo": "https://static2.finnhub.io/file/publicdatany/finnhubimage/stock_logo/AAPL.png",
            "earnings_history": build_earnings_history(
                [
                    earnings_quarter("2025-09-30", 2025, 4, 1.85, 1.81),
                    earnings_quarter("2025-12-31", 2026, 1, 2.84, 2.73),
                    earnings_quarter("2026-03-31", 2026, 2, 2.01, 1.99),
                    earnings_quarter("2026-06-30", 2026, 3, 1.91, 1.93),
                ]
            ),
            "upcoming_earnings": upcoming_earnings("15 Sep 2026", "bmo", 2.14, 102000000000),
            "web_stories": [
                story(0, "AAPL", "Apple expands AI features across iOS developer preview", "Bloomberg", 2),
                story(1, "AAPL", "Services revenue momentum offsets hardware cycle concerns", "Reuters", 4, False),
            ],
            "error": None,
        },
        {
            "ticker": "IN:TCS",
            "display_symbol": "TCS",
            "market": "IN",
            "exchange": "NSE",
            "quote": {"price": 4125.75, "change_pct": 0.85},
            "price_ranges": {
                "year_high": {"value": 4592.25, "distance_pct": 10.16},
                "all_time_high": {"value": 4592.25, "distance_pct": 10.16},
            },
            "logo": None,
            "earnings_history": build_indian_earnings_history(
                [
                    reported_quarter("2025-09-01", "Sep 2025", "Q2 FY26", 34.10, 65799, 12075, 24.6),
                    reported_quarter("2025-12-01", "Dec 2025", "Q3 FY26", 35.22, 67586, 12480, 25.0),
                    reported_quarter("2026-03-01", "Mar 2026", "Q4 FY26", 36.45, 69340, 12910, 25.3),
                    reported_quarter("2026-06-01", "Jun 2026", "Q1 FY27", 37.18, 71220, 13285, 25.7),
                ]
            ),
            "upcoming_earnings": None,
            "web_stories": [
                story(0, "TCS", "TCS wins large deal in European banking sector", "Business Standard", 1),
            ],
            "error": None,
        },
    ]

    for section in sections:
        if section["ticker"] == "IN:TCS":
            section["financial_health"] = sample_financial_health()
    # Illustrative quotes make the compact watchlist's overflow easy to review.
    for ticker, price, change in [
        ("US:MSFT", 420.50, 0.65),
        ("US:AMZN", 185.20, -0.32),
        ("US:GOOGL", 165.80, 0.48),
        ("IN:INFY", 1840.00, -0.72),
        ("IN:HDFCBANK", 1680.25, 0.25),
        ("IN:ICICIBANK", 1245.60, -0.18),
    ]:
        market, symbol = ticker.split(":")
        sections.append({
            "ticker": ticker, "display_symbol": symbol, "market": market,
            "exchange": "NSE" if market == "IN" else "US",
            "quote": {"price": price, "change_pct": change},
            "web_stories": [], "error": None,
        })
    tickers = [section["ticker"] for section in sections]
    ai_summary = {
        "market_context": (
            "AI infrastructure demand and resilient digital-services spending are driving the "
            "stronger names, while investors weigh company-specific execution and margin trends."
        ),
        "ticker_summaries": {
            "US:NVDA": (
                "Product-roadmap momentum and sustained data-center demand remain the central "
                "themes ahead of the next earnings update."
            ),
            "IN:RELIANCE": (
                "Steady refining margins and continued Jio subscriber growth provide support "
                "despite the modest share-price decline."
            ),
            "US:AAPL": (
                "New AI features and services growth are helping offset investor concerns about "
                "the pace of the hardware replacement cycle."
            ),
            "IN:TCS": (
                "The latest European banking win reinforces demand for large transformation deals "
                "and supports the stock's positive move."
            ),
        },
    }
    html = build_web_digest(
        sections,
        tickers,
        fetched_at_label="Fetched at 9:15 AM ET · Aug 15, 2026",
        fetched_at_iso="2026-08-15T13:15:00+00:00",
        ai_summary=ai_summary,
        financial_health_summaries={"IN:TCS": {"judgement": "Mixed", "summary": "Operating cash flow covers investment spending, while profit margins have narrowed."}},
        subscribe_enabled_override=True,
        prefill_email="investor@example.com",
    )
    html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"
    output_dir = ROOT / "public" / ("legacy" if resolve_design() == "legacy" else "")
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / "preview-digest.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out} ({len(html)} bytes)")
    print(f"Open http://localhost:8765/{out.relative_to(ROOT / 'public').as_posix()}")


if __name__ == "__main__":
    main()
