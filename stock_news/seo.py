"""Public page metadata without adding upstream requests to page rendering."""

import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

# Keep this origin aligned with the static homepage, robots.txt and sitemap.
SITE_ORIGIN = "https://www.mydailydigest.online"


@lru_cache(maxsize=1)
def company_names():
    path = Path(__file__).resolve().parent.parent / "config" / "in_entities_cache.json"
    return {item["symbol"]: item["name"] for item in json.loads(path.read_text())["entities"]}


def company_metadata(symbol, *, ai=False, name=None):
    ticker = symbol.removeprefix("IN:")
    name = name or company_names().get(ticker, ticker)
    if ai:
        title = f"{name} ({ticker}) AI Overview | Tickr Digest"
        description = f"Explore an evidence-linked AI overview of {name} ({ticker}), with company, market and financial context. Verify the sources in full stock details."
    else:
        title = f"{name} ({ticker}) Share Price, Financials & News | Tickr Digest"
        description = f"Research {name} ({ticker}): share price, reported financials, ownership and recent news. Explore sourced Indian company data with Tickr Digest."
    path = "/ai-overview/" if ai else "/stocks/"
    return {"title": title, "description": description,
            "canonical": SITE_ORIGIN + path + quote(symbol, safe=":"),
            "stock_path": "/stocks/" + quote(symbol, safe=":"),
            "image": SITE_ORIGIN + "/assets/tickr-digest-icon-t-concept.png"}


def snapshot_context(snapshot):
    """Bound the visible overview while retaining original units and periods."""
    from stock_news.stock_detail import safe_url, validate_request, StockDataError
    core = snapshot['data']
    metrics = [metric for group in (core.get('health') or {}).get('groups', [])
               for metric in group.get('metrics', []) if metric.get('value') is not None]
    peers = []
    for peer in core.get('peers', [])[:8]:
        try:
            candidate = peer.get('symbol')
            if not isinstance(candidate, str):
                continue
            symbol = validate_request(candidate)
        except StockDataError:
            continue
        peers.append({'name': peer.get('companyName') or symbol[3:],
                      'path': '/stocks/' + quote(symbol, safe=':')})
    return {'page_core': core, 'snapshot': snapshot,
            'facts': metrics[:16], 'peers': peers,
            'stories': [{**story, 'url': safe_url(story.get('url'))}
                        for story in core.get('news', [])[:5]],
            'format_number': lambda value: format(value, ',.2f').rstrip('0').rstrip('.')
                if isinstance(value, (int, float)) else str(value)}
