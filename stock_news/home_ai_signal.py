"""Daily homepage selection from IndianAPI's verified trending gainers."""
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import math
import re
import threading
import time

import requests

from stock_news import indianapi
from stock_news.stock_detail import StockDataError, normalize_core, validate_request
from stock_news.stock_ai_overview import get_stock_ai_overview

TTL_SECONDS = 86400
NO_MATCH_TTL = 300
_cache = {}
_pending = {}
_lock = threading.Lock()


def numeric(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(str(value).replace(',', ''))
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def _identity(name):
    return ' '.join(re.sub(r'\b(ltd|limited)\b', '', re.sub(r'[^a-z0-9]+', ' ', str(name).lower())).split())


def _request(endpoint, params, key, root):
    response = requests.get(f'{root}/{endpoint}', params=params,
                            headers=indianapi._headers(key), timeout=(4, 18))
    response.raise_for_status()
    return response.json()


def _candidate(row, key, root):
    try:
        payload = _request('stock', {'name': row['company_name']}, key, root)
        if not isinstance(payload, dict) or _identity(payload.get('companyName')) != _identity(row['company_name']):
            return None, False
        profile = payload.get('companyProfile') or {}
        bare = profile.get('exchangeCodeNse') or profile.get('exchangeCodeNsi')
        if not isinstance(bare, str) or not bare.strip():
            return None, False
        symbol = validate_request('IN:' + bare.strip().upper())
        cap = numeric((payload.get('stockDetailsReusableData') or {}).get('marketCap'))
        if cap is None or cap <= 0:
            return None, False
        return (row, payload, symbol, cap), False
    except requests.RequestException:
        return None, True
    except (ValueError, TypeError, AttributeError, StockDataError):
        return None, False


def _build(key, root):
    trending = _request('trending', {}, key, root)
    group = trending.get('trending_stocks') if isinstance(trending, dict) else None
    if not isinstance(group, dict) or not isinstance(group.get('top_gainers'), list):
        raise ValueError('Invalid trending response')
    rows = [row for row in group['top_gainers'] if isinstance(row, dict)
            and isinstance(row.get('company_name'), str) and row['company_name'].strip()
            and (numeric(row.get('percent_change')) or 0) > 0]
    rows.sort(key=lambda row: numeric(row['percent_change']), reverse=True)
    winner, partial_failure = None, False
    # Verify every gainer's market cap, with three upstream reads at a time.
    with ThreadPoolExecutor(max_workers=3) as pool:
        for start in range(0, len(rows), 3):
            for candidate, failed in pool.map(lambda row: _candidate(row, key, root), rows[start:start + 3]):
                partial_failure |= failed
                if candidate:
                    if winner is None or candidate[3] > winner[3]:
                        winner = candidate
    if not winner:
        return {'ok': False, 'code': 'no_match', 'error': 'No qualifying trending stock is available.'}, (0 if partial_failure else NO_MATCH_TTL)
    row, raw, symbol, cap = winner
    core = normalize_core(raw, symbol)
    selected_at = datetime.now(timezone.utc).isoformat()
    stock = {'name': core['name'], 'symbol': symbol, 'industry': core['industry'],
             'market_cap_crore': cap, 'selection': 'highest_market_cap',
             'price': numeric(row.get('price')), 'percent_change': numeric(row['percent_change']),
             'exchange': row.get('exchange_type'),
             'source_time': ' '.join(str(row.get(k) or '') for k in ('date', 'time')).strip(),
             'selected_at': selected_at}
    try:
        overview, _ = get_stock_ai_overview(symbol, core)
    except Exception:
        overview = None
    visual_core = {field: core.get(field) for field in (
        'name', 'industry', 'prices', 'change_percent', 'year_low', 'year_high',
        'snapshot', 'health', 'source_time')}
    return {'ok': True, 'stock': stock, 'core': visual_core, 'overview': overview,
            'ai_available': bool(overview)}, (TTL_SECONDS if overview and not partial_failure else 0)


def get_home_ai_signal(key):
    if not key:
        return {'ok': False, 'code': 'unavailable', 'error': 'Trending stock signals are temporarily unavailable.'}, 0
    root = indianapi._api_root()
    cache_key = (root, hashlib.sha256(key.encode()).hexdigest())
    with _lock:
        cached = _cache.get(cache_key)
        if cached and cached[0] > time.monotonic():
            return cached[1], max(1, int(cached[0] - time.monotonic()))
        future = _pending.get(cache_key)
        owner = future is None
        if owner:
            future = _pending[cache_key] = Future()
    if not owner:
        try:
            return future.result(timeout=180)
        except TimeoutError:
            return {'ok': False, 'code': 'unavailable',
                    'error': 'Trending stock signals are temporarily unavailable.'}, 0
    try:
        result, ttl = _build(key, root)
        if ttl:
            with _lock:
                if len(_cache) >= 8:
                    _cache.pop(next(iter(_cache)))
                _cache[cache_key] = (time.monotonic() + ttl, result)
        future.set_result((result, ttl))
        return result, ttl
    except Exception:
        response = ({'ok': False, 'code': 'unavailable',
                     'error': 'Trending stock signals are temporarily unavailable.'}, 0)
        future.set_result(response)
        return response
    finally:
        with _lock:
            _pending.pop(cache_key, None)
