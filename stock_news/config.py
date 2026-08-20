"""Paths, constants, and environment configuration."""

import os
import re
from datetime import time as time_of_day
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
TICKER_ALIASES_PATH = REPO_ROOT / "config" / "ticker_aliases.json"
TEMPLATES_PATH = REPO_ROOT / "templates"

MAX_TICKERS_PER_USER = 10
HEADLINES_PER_TICKER = 3
WEB_HEADLINES_PER_TICKER = 10
FETCH_LIMIT_PER_TICKER = 10
SUMMARY_EXCERPT_LENGTH = 160
MIN_RELEVANCE_SCORE = 3
MIN_STORIES_PER_TICKER = 2
HEADLINE_ALIAS_POINTS = 3
SUMMARY_ALIAS_POINTS = 1
TICKER_SYMBOL_BONUS = 1
RIVAL_PENALTY = 3
DIGEST_HEADING = "Your stock news briefing"
SEND_DELAY_SECONDS = 2
MAX_SUBJECT_MOVERS = 3
MAX_SUBJECT_HEADLINES = 3
SUBJECT_MAX_LEN = 78
HEADLINE_SNIPPET_LEN = 32

ET_ZONE = ZoneInfo("America/New_York")
MARKET_OPEN_ET = time_of_day(9, 30)
MARKET_CLOSE_ET = time_of_day(16, 0)
TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")

PUBLISHER_LOGO_MARKERS = (
    "yahoo_finance",
    "/rz/stage/p/",
    "yimg.com/rz/",
    "seekingalpha.com/assets/images/sa_logo",
    "benzinga.com/sites/all/themes/benzinga",
    "foolcdn.com/media/affiliates/logos",
)

FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY")
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
DIGEST_SIGNING_SECRET = os.environ.get("DIGEST_SIGNING_SECRET", "")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_DOI_TEMPLATE_ID = os.environ.get("BREVO_DOI_TEMPLATE_ID", "").strip()
# Canonical list: Daily Digest - US. Subscribe and cron always use this id.
BREVO_LIST_ID = "7"
BREVO_TICKERS_ATTRIBUTE = os.environ.get("BREVO_TICKERS_ATTRIBUTE", "US_TICKERS").strip().upper()
EMAIL_FROM = os.environ.get("EMAIL_FROM", "").strip()
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Tickr Digest").strip()

US_SYMBOL_TYPES = frozenset({"Common Stock", "ETF", "ETP", "ADR", "ETN", "ETC", "Closed-End Fund"})
FOREIGN_SYMBOL_SUFFIXES = (".DE", ".L", ".TO", ".HK", ".SW", ".PA", ".AS", ".MI", ".AX", ".KS", ".TW")
