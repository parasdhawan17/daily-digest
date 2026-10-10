import io
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import requests
from stock_news import home_ai_signal as signal
from api.home_ai_signal import handle_get
from api.index import route


def row(name, change):
    return {'company_name': name, 'percent_change': change, 'price': '100',
            'date': '2026-10-09', 'time': '10:00', 'exchange_type': 'BSE'}


def stock(name, cap, symbol=None):
    return {'companyName': name, 'companyProfile': {'exchangeCodeNse': symbol or name},
            'stockDetailsReusableData': {'marketCap': cap}, 'industry': 'Software'}


class HomeSignalTests(unittest.TestCase):
    def setUp(self):
        signal._cache.clear()
        signal._pending.clear()

    def build(self, rows, caps):
        def request(endpoint, params, key, root):
            if endpoint == 'trending':
                return {'trending_stocks': {'top_gainers': rows}}
            value = caps[params['name']]
            if isinstance(value, Exception):
                raise value
            return value
        with patch.object(signal, '_request', side_effect=request) as fetch, patch.object(signal, 'get_stock_ai_overview', return_value=({'ok': True, 'data': {'summary': {}}}, 21600)) as ai:
            result, ttl = signal.get_home_ai_signal('key')
            return result, ttl, fetch, ai

    def test_highest_market_cap_and_payload_reuse(self):
        result, ttl, fetch, ai = self.build([row('A', '9'), row('B', '10'), row('C', '11')],
                                          {'A': stock('A', 200000), 'B': stock('B', 100000), 'C': stock('C', 99999)})
        self.assertEqual(result['stock']['symbol'], 'IN:A')
        self.assertEqual(result['stock']['selection'], 'highest_market_cap')
        self.assertEqual(result['core']['snapshot']['marketCap'], 200000)
        self.assertNotIn('companyProfile', result['core'])
        self.assertEqual(ttl, 86400)
        self.assertEqual(fetch.call_count, 4)
        ai.assert_called_once()
        self.assertEqual(ai.call_args.args[1]['snapshot']['marketCap'], 200000)

    def test_small_caps_and_later_batches_are_considered(self):
        result, ttl, fetch, _ = self.build(
            [row('A', 12), row('B', 10), row('C', 8), row('D', 6)],
            {'A': stock('A', 10), 'B': stock('B', 20),
             'C': stock('C', 30), 'D': stock('D', '1,000')})
        self.assertEqual(result['stock']['symbol'], 'IN:D')
        self.assertEqual(result['stock']['market_cap_crore'], 1000)
        self.assertEqual(ttl, 86400)
        self.assertEqual(fetch.call_count, 5)

    def test_equal_caps_prefer_higher_gain(self):
        result, _, _, _ = self.build([row('A', 8), row('B', 12)],
                                    {'A': stock('A', 100), 'B': stock('B', 100)})
        self.assertEqual(result['stock']['symbol'], 'IN:B')

    def test_invalid_changes_and_identity(self):
        result, ttl, _, ai = self.build([row('A', 'NaN'), row('B', '-1'), row('C', 'Infinity'), row('D', '3')],
                                       {'D': stock('OTHER', 1000000)})
        self.assertEqual(result['code'], 'no_match')
        self.assertEqual(ttl, 300)
        ai.assert_not_called()

    def test_no_match_and_missing_symbol_or_cap(self):
        result, ttl, _, ai = self.build([row('A', 5), row('B', 4), row('C', 3)],
                                       {'A': stock('A', 0), 'B': stock('B', float('nan')), 'C': stock('C', 500000, ' ')})
        self.assertEqual(result['code'], 'no_match')
        self.assertEqual(ttl, 300)
        ai.assert_not_called()

    def test_partial_failure_is_not_cached(self):
        result, ttl, _, _ = self.build([row('A', 10), row('B', 9)],
                                     {'A': requests.Timeout(), 'B': stock('B', 200000)})
        self.assertTrue(result['ok'])
        self.assertEqual(ttl, 0)
        self.assertFalse(signal._cache)

    def test_cache_hit_and_expiry(self):
        payload = {'ok': True}
        with patch.object(signal, '_build', return_value=(payload, 86400)) as build, patch.object(signal.time, 'monotonic', return_value=100):
            self.assertEqual(signal.get_home_ai_signal('key'), (payload, 86400))
            signal.get_home_ai_signal('key')
            self.assertEqual(build.call_count, 1)
        with patch.object(signal, '_build', return_value=(payload, 86400)) as build, patch.object(signal.time, 'monotonic', return_value=86501):
            signal.get_home_ai_signal('key')
            build.assert_called_once()

    def test_short_no_match_cache(self):
        with patch.object(signal, '_build', return_value=({'ok': False, 'code': 'no_match'}, 300)) as build:
            signal.get_home_ai_signal('key'); signal.get_home_ai_signal('key')
            build.assert_called_once()

    def test_failure_and_ai_unavailable_not_cached(self):
        with patch.object(signal, '_build', side_effect=requests.Timeout()) as build:
            signal.get_home_ai_signal('key'); signal.get_home_ai_signal('key')
            self.assertEqual(build.call_count, 2)
            self.assertFalse(signal._cache)
        signal._cache.clear()
        with patch.object(signal, '_request', side_effect=lambda endpoint, *args: {'trending_stocks': {'top_gainers': [row('A', 5)]}} if endpoint == 'trending' else stock('A', 100000)), patch.object(signal, 'get_stock_ai_overview', return_value=(None, 0)):
            result, ttl = signal.get_home_ai_signal('key')
            self.assertTrue(result['ok']); self.assertIsNone(result['overview']); self.assertEqual(ttl, 0)

    def test_coalesces_requests(self):
        entered, release = threading.Event(), threading.Event()
        def build(*args):
            entered.set(); release.wait(2)
            return {'ok': True}, 86400
        with patch.object(signal, '_build', side_effect=build) as mock, ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(signal.get_home_ai_signal, 'key')
            self.assertTrue(entered.wait(2))
            second = pool.submit(signal.get_home_ai_signal, 'key')
            release.set()
            self.assertEqual(first.result(), second.result())
            mock.assert_called_once()

    def test_route_and_cache_headers(self):
        class Handler:
            path = '/api/home-ai-signal'
            headers = {}
            wfile = io.BytesIO()
            sent = {}
            def send_response(self, status): self.status = status
            def send_header(self, key, value): self.sent[key] = value
            def end_headers(self): pass
        handler = Handler()
        self.assertEqual(route(handler), 'home-ai-signal')
        handler.path = '/api/index?route=home-ai-signal'
        self.assertEqual(route(handler), 'home-ai-signal')
        with patch('api.home_ai_signal.get_home_ai_signal', return_value=({'ok': True}, 86400)):
            handle_get(handler)
            self.assertEqual(handler.sent['Cache-Control'], 'public, max-age=0, s-maxage=86400')
        with patch('api.home_ai_signal.get_home_ai_signal', return_value=({'ok': False}, 0)):
            handle_get(handler)
            self.assertEqual(handler.status, 503)
            self.assertEqual(handler.sent['Cache-Control'], 'no-store')
        config = json.loads(__import__('pathlib').Path('vercel.json').read_text())
        self.assertTrue(any(item['source'] == '/api/home-ai-signal' for item in config['rewrites']))
