"""Public stock research data, with bounded, coalesced upstream reads.

Only this module's allowlisted requests can reach IndianAPI. The process cache
is bounded and supplements the CDN cache; neither stores failures or secrets.
"""
from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import Future
from datetime import datetime, timezone
import hashlib
from html import unescape
import json
import threading
import time
from urllib.parse import urlparse, urljoin

import requests

from stock_news import indianapi
from stock_news.financial_health import build_financial_health, number
from stock_news.markets import parse_ticker, format_prefixed

PERIODS = ('1m', '6m', '1yr', '3yr', '5yr', '10yr', 'max')
SERIES = ('quarter_results', 'yoy_results', 'balancesheet', 'cashflow', 'ratios',
          'shareholding_pattern_quarterly', 'shareholding_pattern_yearly')
TTLS = {'core': 300, 'history': 3600, 'financials': 21600, 'targets': 21600, 'forecasts': 21600}
_cache: OrderedDict = OrderedDict()
_pending: dict[tuple, Future] = {}
_lock = threading.Lock()
_MAX_CACHE = 96
_INTERNAL = {'dataStatus', 'lastSuccessfulRefresh', 'lastRefreshAttempt', 'refreshPending',
             'refreshError', 'fallbackSections', 'colorCode', 'languageSupport', 'videoBody'}


class StockDataError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code = status, code


def validate_request(symbol, section='core', period='1yr', series='quarter_results'):
    parsed = parse_ticker(symbol)
    if not parsed or parsed[0] != 'IN':
        raise StockDataError(400, 'invalid_symbol', 'Choose a valid Indian stock symbol.')
    if section not in TTLS or period not in PERIODS or series not in SERIES:
        raise StockDataError(400, 'invalid_section', 'This data selection is not supported.')
    return 'IN:' + parsed[1]


def safe_url(value):
    if not isinstance(value, str):
        return None
    try:
        url = urlparse(value.strip())
        return value.strip() if url.scheme in ('https', 'http') and url.hostname and not url.username else None
    except ValueError:
        return None


def clean(value):
    """Keep provider data, minus operational fields and unsafe markup/links."""
    if isinstance(value, dict):
        return {k: (safe_url(v) if k.lower() in ('url', 'imageurl', 'website', 'link', 'listimage', 'thumbnailimage') else clean(v))
                for k, v in value.items() if k not in _INTERNAL}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, str):
        return indianapi._strip_html(unescape(value))
    if isinstance(value, float) and number(value) is None:
        return None
    return value


def _dict(value):
    return value if isinstance(value, dict) else {}


def _list(value):
    return value if isinstance(value, list) else []


def _peer_symbol(peer, entities):
    for key in ('exchangeCodeNse', 'exchangeCodeNsi', 'symbol'):
        value = peer.get(key)
        if value:
            symbol = format_prefixed('IN', str(value).removeprefix('IN:'))
            if symbol:
                return symbol
    name = str(peer.get('companyName', '')).casefold().strip()
    for entity in entities:
        if str(entity.get('name', '')).casefold().strip() == name:
            return format_prefixed('IN', entity.get('symbol', ''))
    # Provider tickerId is often an internal S-code, not an exchange symbol.
    return None


def normalize_core(payload, symbol):
    if not isinstance(payload, dict) or not payload.get('companyName'):
        raise StockDataError(404, 'not_found', 'We could not find this company.')
    profile = _dict(payload.get('companyProfile'))
    returned_symbol = profile.get('exchangeCodeNse') or profile.get('exchangeCodeNsi')
    if returned_symbol and str(returned_symbol).upper() != symbol[3:]:
        raise StockDataError(404, 'not_found', 'No exact match was found for this stock symbol.')
    reusable = _dict(payload.get('stockDetailsReusableData'))
    statements, seen = [], set()
    for record in _list(payload.get('financials')) + _list(payload.get('stockFinancialData')):
        if not isinstance(record, dict):
            continue
        identity = json.dumps(record, sort_keys=True)
        if identity not in seen:
            seen.add(identity)
            statements.append(clean(record))
    statements.sort(key=lambda x: str(x.get('EndDate') or ''), reverse=True)
    peers = _list(profile.get('peerCompanyList')) or _list(reusable.get('peerCompanyList'))
    entities = indianapi._load_entities_cache()
    peers = [{**clean(p), 'symbol': _peer_symbol(p, entities)} for p in peers if isinstance(p, dict)]
    news = []
    for story in _list(payload.get('recentNews')):
        if not isinstance(story, dict):
            continue
        story_url = story.get('url') or story.get('link')
        # The stock endpoint returns Mint article paths as well as absolute URLs.
        if isinstance(story_url, str) and story_url.startswith('/') and not story_url.startswith('//') and '\\' not in story_url:
            story_url = urljoin('https://www.livemint.com', story_url)
        news.append({
            'headline': clean(story.get('headline') or story.get('title') or 'Company news'),
            'summary': clean(story.get('summary') or story.get('description') or ''),
            'url': safe_url(story_url),
            'image': safe_url(indianapi._news_image(story)),
            'date': story.get('lastPublishedDate') or story.get('date') or story.get('published_at'),
            'source': clean(story.get('source') or story.get('publisher') or ''),
        })
    try:
        health = build_financial_health({**payload, 'financials': statements})
    except (TypeError, ValueError, OverflowError, AttributeError):
        health = None
    prices = _dict(payload.get('currentPrice'))
    return {
        'symbol': symbol, 'name': clean(payload['companyName']), 'industry': clean(payload.get('industry')),
        'prices': {exchange: number(prices.get(exchange)) for exchange in ('NSE', 'BSE')},
        'change_percent': number(payload.get('percentChange')),
        'year_high': number(payload.get('yearHigh')), 'year_low': number(payload.get('yearLow')),
        'source_time': ' '.join(str(reusable.get(k) or '') for k in ('date', 'time')).strip() or None,
        'profile': clean({k: v for k, v in profile.items() if k not in ('peerCompanyList',)}),
        'peers': peers, 'financials': statements, 'metrics': clean(_dict(payload.get('keyMetrics'))),
        'health': health, 'ownership': clean(_list(payload.get('shareholding'))),
        'actions': clean(_dict(payload.get('stockCorporateActionData'))), 'news': news,
        'technical': clean(payload.get('stockTechnicalData')), 'risk': clean(payload.get('riskMeter')),
        'ratings': clean(payload.get('analystView')), 'recommendations': clean(payload.get('recosBar')),
        'snapshot': clean({k: v for k, v in reusable.items() if k not in ('peerCompanyList', 'stockAnalyst')}),
        'futures': clean({'expiryDates': payload.get('futureExpiryDates'), 'overview': payload.get('futureOverviewData')}),
        'additional_financials': clean(payload.get('initialStockFinancialData')),
    }


def _fetch(symbol, section, period, series, key, root):
    bare = symbol[3:]
    endpoint, params = {
        'core': ('stock', {'name': bare}),
        'history': ('historical_data', {'stock_name': bare, 'period': period, 'filter': 'price'}),
        'financials': ('historical_stats', {'stock_name': bare, 'stats': series}),
        'targets': ('stock_target_price', {'stock_id': bare.lower()}),
        'forecasts': ('stock_forecasts', {'stock_id': bare.lower(), 'measure_code': 'EPS',
                      'period_type': 'Annual', 'data_type': 'Estimates', 'age': 'Current'}),
    }[section]
    try:
        response = requests.get(f'{root}/{endpoint}', params=params, headers=indianapi._headers(key), timeout=(4, 18))
        if response.status_code in (401, 403):
            raise StockDataError(403, 'unavailable', 'This data is not available with the current provider access.')
        if response.status_code == 429:
            raise StockDataError(429, 'rate_limited', 'The data provider is busy. Please try again later.')
        if response.status_code == 404:
            if section == 'core':
                raise StockDataError(404, 'not_found', 'We could not find this company.')
            return None
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and (payload.get('error') or payload.get('detail')):
            message = str(payload.get('error') or payload.get('detail')).lower()
            if section == 'core' and any(term in message for term in ('not found', 'no data', 'does not exist')):
                raise StockDataError(404, 'not_found', 'We could not find this company.')
            raise StockDataError(503, 'provider_error', 'The provider could not return this data. Please try again.')
        return normalize_core(payload, symbol) if section == 'core' else clean(payload)
    except (requests.RequestException, ValueError):
        raise StockDataError(503, 'provider_error', 'Stock data is temporarily unavailable. Please try again.') from None


def get_data(symbol, section, period, series, key, root=None):
    symbol = validate_request(symbol, section, period, series)
    if not key:
        raise StockDataError(503, 'not_configured', 'Stock research is temporarily unavailable.')
    root = (root or indianapi._api_root()).rstrip('/')
    cache_key = (root, hashlib.sha256(key.encode()).hexdigest(), symbol, section,
                 period if section == 'history' else '', series if section == 'financials' else '')
    with _lock:
        cached = _cache.get(cache_key)
        if cached and cached[0] > time.monotonic():
            _cache.move_to_end(cache_key)
            return cached[1], max(1, int(cached[0] - time.monotonic()))
        future = _pending.get(cache_key)
        owner = future is None
        if owner:
            if len(_pending) >= 16:
                raise StockDataError(429, 'busy', 'Stock research is busy. Please try again shortly.')
            future = _pending[cache_key] = Future()
    if not owner:
        try:
            return future.result(timeout=25)
        except TimeoutError:
            raise StockDataError(503, 'timeout', 'The provider is taking longer than expected. Please retry.') from None
    try:
        data = _fetch(symbol, section, period, series, key, root)
        envelope = {'ok': True, 'symbol': symbol, 'section': section, 'data': data,
                    'fetched_at': datetime.now(timezone.utc).isoformat(), 'source': 'IndianAPI'}
        ttl = TTLS[section]
        with _lock:
            _cache[cache_key] = (time.monotonic() + ttl, envelope)
            while len(_cache) > _MAX_CACHE:
                _cache.popitem(last=False)
        future.set_result((envelope, ttl))
        return envelope, ttl
    except Exception as error:
        future.set_exception(error)
        raise
    finally:
        with _lock:
            _pending.pop(cache_key, None)
