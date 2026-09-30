import hashlib
import io
import json
import unittest
from unittest.mock import Mock, patch

from api import stock, ai_overview_page
from stock_news import stock_detail as detail


def snapshot(symbol='IN:TCS'):
    return {'ok': True, 'symbol': symbol, 'fetched_at': '2026-09-30T00:00:00+00:00',
            'data': {'name': 'Tata Consultancy Services', 'industry': 'IT',
                     'profile': {'companyDescription': 'Company description </script><script>alert(1)</script>'},
                     'prices': {'NSE': 0, 'BSE': None}, 'source_time': '2026-09-30',
                     'health': {'groups': [{'metrics': [{'label': 'Net profit', 'value': -10,
                                                         'period': 'FY 2026', 'unit': '₹ cr'}]}]},
                     'news': [{'headline': 'Company news', 'summary': 'Reported results',
                               'url': 'javascript:alert(1)', 'source': 'Publisher', 'date': None}],
                     'peers': [{'symbol': 'IN:INFY', 'companyName': 'Infosys'},
                               {'symbol': 'US:AAPL', 'companyName': 'Bad peer'},
                               {'symbol': None, 'companyName': 'Unresolved peer'},
                               {'companyName': 'Missing ticker'}]}}


def handler(path):
    return Mock(path=path, headers={}, wfile=io.BytesIO())


class CompanySnapshotTests(unittest.TestCase):
    def test_initial_html_contains_visible_facts_and_safe_bootstrap_for_both_pages(self):
        for module, path, content_id in [(stock, '/stocks/IN:TCS', 'stock-content'),
                                         (ai_overview_page, '/ai-overview/IN:TCS', 'overview-content')]:
            with self.subTest(path=path), patch.object(detail, 'get_data', return_value=(snapshot(), 300)):
                request = handler(path)
                module.handle_page(request)
                request.send_response.assert_called_once_with(200)
                body = request.wfile.getvalue().decode()
                self.assertIn('id="company-name">Tata Consultancy Services</h1>', body)
                self.assertIn(f'id="{content_id}">', body)
                self.assertIn('Company description &lt;/script&gt;', body)
                self.assertIn('Net profit · FY 2026', body)
                self.assertIn('-10 ₹ cr', body)
                self.assertIn('₹0', body)
                self.assertIn('Company news', body)
                self.assertIn('href="/stocks/IN:INFY"', body)
                self.assertNotIn('href="javascript:', body)
                self.assertNotIn('/stocks/US:AAPL', body)
                seed = body.split('id="company-bootstrap" type="application/json">')[1].split('</script>')[0]
                self.assertNotIn('</script>', seed)
                self.assertEqual(json.loads(seed)['symbol'], 'IN:TCS')

    def test_not_found_and_provider_failures_have_distinct_http_statuses(self):
        for module, prefix in [(stock, '/stocks/'), (ai_overview_page, '/ai-overview/')]:
            for error, expected in [(detail.StockDataError(404, 'not_found', 'Company missing'), 404),
                                    (detail.StockDataError(503, 'provider_error', 'Temporarily unavailable'), 503),
                                    (detail.StockDataError(429, 'rate_limited', 'Provider busy'), 503),
                                    (detail.StockDataError(403, 'unavailable', 'Provider access unavailable'), 503)]:
                with self.subTest(module=module.__name__, status=error.status), \
                     patch.object(module, 'get_page_snapshot', side_effect=error):
                    request = handler(prefix + 'IN:ZZNOTREAL')
                    module.handle_page(request)
                    request.send_response.assert_called_once_with(expected)
                    self.assertNotIn(b'company-bootstrap', request.wfile.getvalue())
                    self.assertIn(b'noindex', request.wfile.getvalue())

    def test_missing_configuration_is_temporary_unavailability(self):
        with patch.dict('os.environ', {'INDIANAPI_API_KEY': ''}), patch.object(detail, '_fetch') as fetch:
            request = handler('/stocks/IN:TCS')
            stock.handle_page(request)
            request.send_response.assert_called_once_with(503)
            fetch.assert_not_called()


class StaleSnapshotTests(unittest.TestCase):
    def setUp(self):
        detail._cache.clear()
        self.addCleanup(detail._cache.clear)
        self.cache_key = ('https://example.com', hashlib.sha256(b'key').hexdigest(),
                          'IN:TCS', 'core', '', '', '')

    def test_recent_cached_snapshot_survives_transient_failure_without_refreshing_age(self):
        detail._cache[self.cache_key] = (100, snapshot())
        with patch.object(detail.indianapi, '_api_root', return_value='https://example.com'), \
             patch.object(detail.time, 'monotonic', return_value=200), \
             patch.object(detail, 'get_data', side_effect=detail.StockDataError(503, 'provider_error', 'Unavailable')):
            result = detail.get_page_snapshot('IN:TCS', 'key')
            self.assertTrue(result['stale'])
            self.assertEqual(result['fetched_at'], snapshot()['fetched_at'])
            self.assertEqual(detail._cache[self.cache_key][0], 100)
            self.assertNotIn('stale', detail._cache[self.cache_key][1])

    def test_not_found_and_old_cache_are_never_served_as_success(self):
        detail._cache[self.cache_key] = (100, snapshot())
        for now, status in [(200, 404), (4000, 503), (200, 403)]:
            with self.subTest(now=now, status=status), \
                 patch.object(detail.indianapi, '_api_root', return_value='https://example.com'), \
                 patch.object(detail.time, 'monotonic', return_value=now), \
                 patch.object(detail, 'get_data', side_effect=detail.StockDataError(status, 'error', 'Unavailable')):
                with self.assertRaises(detail.StockDataError):
                    detail.get_page_snapshot('IN:TCS', 'key')
