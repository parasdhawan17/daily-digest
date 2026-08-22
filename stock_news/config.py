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
PRE_OPEN_SEND_ET = time_of_day(9, 15)
POST_CLOSE_SEND_ET = time_of_day(16, 15)

IST_ZONE = ZoneInfo("Asia/Kolkata")
IN_MARKET_OPEN_IST = time_of_day(9, 30)
IN_MARKET_CLOSE_IST = time_of_day(15, 30)
IN_PRE_OPEN_SEND_IST = time_of_day(9, 15)
IN_POST_CLOSE_SEND_IST = time_of_day(15, 45)

# Only schedule if the target is still ahead and close (cron window).
EMAIL_SCHEDULE_MAX_AHEAD_MINUTES = 30
TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")
IN_ENTITIES_CACHE_PATH = REPO_ROOT / "config" / "in_entities_cache.json"

PUBLISHER_LOGO_MARKERS = (
    "yahoo_finance",
    "/rz/stage/p/",
    "yimg.com/rz/",
    "seekingalpha.com/assets/images/sa_logo",
    "benzinga.com/sites/all/themes/benzinga",
    "foolcdn.com/media/affiliates/logos",
)

FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY")
INDIANAPI_BASE_URL = os.environ.get(
    "INDIANAPI_BASE_URL",
    "https://stock.indianapi.in",
).rstrip("/")
INDIANAPI_API_KEY = os.environ.get("INDIANAPI_API_KEY", "").strip()
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
DIGEST_SIGNING_SECRET = os.environ.get("DIGEST_SIGNING_SECRET", "")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_DOI_TEMPLATE_ID = os.environ.get("BREVO_DOI_TEMPLATE_ID", "").strip()
# Canonical list: Daily Digest - US. Subscribe and cron always use this id.
BREVO_LIST_ID = "7"
BREVO_TICKERS_ATTRIBUTE = os.environ.get("BREVO_TICKERS_ATTRIBUTE", "US_TICKERS").strip().upper()
EMAIL_FROM = os.environ.get("EMAIL_FROM", "").strip()
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Stock News").strip()

US_SYMBOL_TYPES = frozenset({"Common Stock", "ETF", "ETP", "ADR", "ETN", "ETC", "Closed-End Fund"})
FOREIGN_SYMBOL_SUFFIXES = (".DE", ".L", ".TO", ".HK", ".SW", ".PA", ".AS", ".MI", ".AX", ".KS", ".TW")
