import copy
import io
import json
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

import requests

from api import stock, tickers_search
from api.index import route
from stock_news import stock_detail as detail


def company():
    statement = {'Type': 'Annual', 'EndDate': '2026-03-31', 'FiscalYear': '2026',
                 'stockFinancialMap': {'INC': [{'key': 'NetIncome', 'value': '-10'},
                                               {'key': 'TotalRevenue', 'value': '0'}]}}
    return {'companyName': 'Example <b>Ltd</b>', 'companyProfile': {
        'exchangeCodeNse': 'EXAMPLE', 'exchangeCodeBse': '500001',
        'refreshError': 'private provider diagnostics',
        'peerCompanyList': [{'tickerId': 'S0003032', 'companyName': 'Infosys'}]},
        'currentPrice': {'BSE': '0'}, 'percentChange': '-2.5',
        'financials': [statement], 'stockFinancialData': [copy.deepcopy(statement)],
        'recentNews': [{'headline': '<b>A story</b>', 'url': 'javascript:alert(1)',
                        'summary': '<script>bad</script>Summary', 'image': 'https://example.com/image.png'}],
        'keyMetrics': {'growth': [{'value': 0, 'displayName': 'Growth'}]}}


def handler(path):
    h = Mock()
    h.path = path
    h.headers = {}
    h.wfile = io.BytesIO()
    return h


class NormalizationTests(unittest.TestCase):
    def test_deduplicates_preserves_zero_negative_and_missing_exchange(self):
        result = detail.normalize_core(company(), 'IN:EXAMPLE')
        self.assertEqual(len(result['financials']), 1)
        self.assertEqual(result['prices'], {'NSE': None, 'BSE': 0})
        self.assertEqual(result['change_percent'], -2.5)
        self.assertEqual(result['financials'][0]['stockFinancialMap']['INC'][0]['value'], '-10')
        self.assertEqual(result['name'], 'Example Ltd')
        self.assertNotIn('refreshError', result['profile'])
        self.assertIsNone(result['news'][0]['url'])
        self.assertEqual(result['peers'][0]['symbol'], 'IN:INFY')

    def test_mixed_periods_and_distinct_statement_bases_survive(self):
        p = company()
        p['financials'] += [{**p['financials'][0], 'Type': 'Interim', 'EndDate': '2026-06-30'},
                            {**p['financials'][0], 'basis': 'Standalone'}]
        result = detail.normalize_core(p, 'IN:EXAMPLE')
        self.assertEqual(len(result['financials']), 3)
        self.assertEqual(result['financials'][0]['EndDate'], '2026-06-30')

    def test_sparse_payload_does_not_invent_data(self):
        result = detail.normalize_core({'companyName': 'Sparse', 'financials': None,
                                        'companyProfile': [], 'keyMetrics': None}, 'IN:SPARSE')
        self.assertEqual(result['prices'], {'NSE': None, 'BSE': None})
        self.assertIsNone(result['source_time'])
        self.assertEqual(result['financials'], [])

    def test_wrong_company_is_not_presented_under_requested_symbol(self):
        with self.assertRaises(detail.StockDataError) as error:
            detail.normalize_core(company(), 'IN:TCS')
        self.assertEqual(error.exception.status, 404)

    def test_internal_peer_identifier_is_not_an_exchange_symbol(self):
        self.assertIsNone(detail._peer_symbol({'tickerId': 'S12345', 'companyName': 'Unknown'}, []))

    def test_provider_relative_news_links_and_entities(self):
        p = company()
        p['recentNews'] = [{'headline': 'Company&nbsp;update', 'url': '/companies/news/story.html'},
                           {'headline': 'Unsafe', 'url': '//evil.example/path'}]
        news = detail.normalize_core(p, 'IN:EXAMPLE')['news']
        self.assertEqual(news[0]['url'], 'https://www.livemint.com/companies/news/story.html')
        self.assertEqual(news[0]['headline'], 'Company\xa0update')
        self.assertIsNone(news[1]['url'])

    def test_safe_urls_and_nonfinite_numbers(self):
        for value in ['javascript:alert(1)', 'data:text/html,hello', '//evil.com', 'https://user:secret@example.com', 'https://[']:
            self.assertIsNone(detail.safe_url(value))
        self.assertEqual(detail.safe_url('https://example.com/a'), 'https://example.com/a')
        self.assertIsNone(detail.clean(float('nan')))


class RequestTests(unittest.TestCase):
    def setUp(self):
        with detail._lock:
            detail._cache.clear()
            detail._pending.clear()

    def test_allowlists_prevent_arbitrary_requests(self):
        for symbol, section, period, series in [('US:TCS', 'core', '1yr', 'ratios'),
                ('IN:../../x', 'core', '1yr', 'ratios'), ('IN:TCS', 'secrets', '1yr', 'ratios'),
                ('IN:TCS', 'history', '1day', 'ratios'), ('IN:TCS', 'financials', '1yr', 'unknown')]:
            with self.assertRaises(detail.StockDataError):
                detail.validate_request(symbol, section, period, series)
        self.assertEqual(detail.validate_request('in:m&m'), 'IN:M&M')

    @patch.object(detail, '_fetch')
    def test_cache_expiry_and_selection_keys(self, fetch):
        fetch.return_value = {'value': 1}
        a, ttl = detail.get_data('IN:TCS', 'core', '1yr', 'quarter_results', 'test-key')
        b, remaining = detail.get_data('IN:TCS', 'core', 'max', 'ratios', 'test-key')
        self.assertIs(a, b)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(ttl, 300)
        self.assertLessEqual(remaining, ttl)
        detail.get_data('IN:TCS', 'history', '1m', 'ratios', 'test-key')
        detail.get_data('IN:TCS', 'history', '1yr', 'ratios', 'test-key')
        self.assertEqual(fetch.call_count, 3)
        with patch.object(detail.time, 'monotonic', return_value=time.monotonic() + 400):
            detail.get_data('IN:TCS', 'core', '1yr', 'ratios', 'test-key')
        self.assertEqual(fetch.call_count, 4)

    @patch.object(detail, '_fetch')
    def test_errors_are_not_cached(self, fetch):
        fetch.side_effect = detail.StockDataError(429, 'rate_limited', 'Busy')
        for _ in range(2):
            with self.assertRaises(detail.StockDataError):
                detail.get_data('IN:TCS', 'core', '1yr', 'ratios', 'key')
        self.assertEqual(fetch.call_count, 2)
        self.assertFalse(detail._cache)
        self.assertFalse(detail._pending)

    @patch.object(detail, '_fetch')
    def test_concurrent_requests_are_coalesced(self, fetch):
        entered, release = threading.Event(), threading.Event()
        def upstream(*args):
            entered.set()
            release.wait(2)
            return {'value': 1}
        fetch.side_effect = upstream
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(detail.get_data, 'IN:TCS', 'targets', '1yr', 'ratios', 'key') for _ in range(3)]
            self.assertTrue(entered.wait(1))
            release.set()
            results = [f.result() for f in futures]
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(results[0][0], results[2][0])
        self.assertEqual(results[0][1], 21600)

    @patch.object(detail.requests, 'get')
    def test_upstream_statuses_and_credentials(self, get):
        for status, code in [(401, 'unavailable'), (403, 'unavailable'), (429, 'rate_limited'), (404, 'not_found')]:
            get.return_value = Mock(status_code=status)
            with self.assertRaises(detail.StockDataError) as error:
                detail._fetch('IN:TCS', 'core', '1yr', 'ratios', 'secret', 'https://example.com')
            self.assertEqual(error.exception.code, code)
        self.assertEqual(get.call_args.kwargs['headers']['x-api-key'], 'secret')
        self.assertNotIn('secret', get.call_args.args[0])
        get.side_effect = requests.Timeout('request with private details')
        with self.assertRaises(detail.StockDataError) as error:
            detail._fetch('IN:TCS', 'history', '1yr', 'ratios', 'secret', 'https://example.com')
        self.assertNotIn('private', str(error.exception))


class EndpointTests(unittest.TestCase):
    def test_routes_local_and_vercel_rewrites(self):
        self.assertEqual(route(handler('/stocks/IN:TCS')), 'stock')
        self.assertEqual(route(handler('/api/index?route=stock&symbol=IN:TCS')), 'stock')
        self.assertEqual(route(handler('/api/stock-data?symbol=IN:TCS')), 'stock-data')

    def test_page_is_public_and_escaped(self):
        h = handler('/stocks/IN:M%26M')
        stock.handle_page(h)
        h.send_response.assert_called_with(200)
        self.assertIn(b'data-symbol="IN:M&amp;M"', h.wfile.getvalue())
        self.assertNotIn(b'credential', h.wfile.getvalue())

    def test_invalid_page(self):
        h = handler('/stocks/US:AAPL')
        stock.handle_page(h)
        h.send_response.assert_called_with(404)

    def test_path_identity_wins_over_query_and_rewrite_works(self):
        h = handler('/stocks/IN:TCS?symbol=IN:INFY')
        stock.handle_page(h)
        self.assertIn(b'data-symbol="IN:TCS"', h.wfile.getvalue())
        h = handler('/api/index?route=stock&symbol=IN:TCS')
        stock.handle_page(h)
        self.assertIn(b'data-symbol="IN:TCS"', h.wfile.getvalue())

    @patch.object(stock, 'get_data', return_value=({'ok': True, 'data': {}}, 300))
    def test_only_one_public_cache_header(self, get):
        h = handler('/api/stock-data?symbol=IN:TCS')
        stock.handle_data(h)
        cache = [call.args for call in h.send_header.call_args_list if call.args[0] == 'Cache-Control']
        self.assertEqual(cache, [('Cache-Control', 'public, max-age=0, s-maxage=300')])

    @patch.object(stock, 'get_data', side_effect=detail.StockDataError(503, 'provider_error', 'Unavailable'))
    def test_errors_have_no_store(self, get):
        h = handler('/api/stock-data?symbol=IN:TCS')
        stock.handle_data(h)
        h.send_header.assert_any_call('Cache-Control', 'no-store')
        self.assertEqual(json.loads(h.wfile.getvalue())['code'], 'provider_error')

    @patch.dict('os.environ', {'INDIANAPI_API_KEY': 'key'})
    @patch.object(tickers_search, 'search_symbols', return_value=[])
    def test_market_filter_and_backward_compatibility(self, search):
        for path, expected in [('/api/tickers/search?q=tcs&market=IN', 'IN'), ('/api/tickers/search?q=tcs', None)]:
            h = handler(path)
            tickers_search.handle_get(h)
            self.assertEqual(search.call_args.kwargs['market'], expected)
            h.send_response.assert_called_with(200)


if __name__ == '__main__':
    unittest.main()
