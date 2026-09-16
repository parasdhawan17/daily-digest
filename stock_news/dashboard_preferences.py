"""Canonical Indian dashboard-card preferences shared with the browser catalog."""
from __future__ import annotations

import json
from functools import lru_cache

from stock_news.config import REPO_ROOT

CATALOG_PATH = REPO_ROOT / "public" / "dashboard-catalog.json"


@lru_cache(maxsize=1)
def catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def allowed_cards() -> tuple[str, ...]:
    return tuple(card["id"] for category in catalog()["categories"] for card in category["cards"])


def default_cards() -> list[str]:
    return [card["id"] for category in catalog()["categories"] if category.get("default")
            for card in category["cards"]]


def parse_dashboard_cards(value, *, default_if_empty: bool = True) -> list[str]:
    if isinstance(value, str):
        values = [item.strip() for item in value.split(",")]
    elif isinstance(value, (list, tuple)):
        values = [str(item).strip() for item in value]
    else:
        values = []
    requested = set(filter(None, values))
    result = [card for card in allowed_cards() if card in requested]
    return result or (default_cards() if default_if_empty else [])


def serialize_dashboard_cards(value) -> str:
    return ", ".join(parse_dashboard_cards(value, default_if_empty=False))
