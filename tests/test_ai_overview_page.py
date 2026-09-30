import io
import unittest
from unittest.mock import Mock, patch

from api import ai_overview_page
from api.index import route


def handler(path, original_url=None):
    request = Mock()
    request.path = path
    request.headers = {'x-vercel-original-url': original_url} if original_url else {}
    request.wfile = io.BytesIO()
    return request


class AIOverviewPageTests(unittest.TestCase):
    def setUp(self):
        def snapshot(symbol, key):
            from stock_news.seo import company_names
            return {'ok': True, 'symbol': symbol, 'fetched_at': '2026-09-30T00:00:00+00:00',
                    'data': {'name': company_names().get(symbol[3:], symbol[3:]),
                             'profile': {}, 'prices': {'NSE': 0, 'BSE': None},
                             'source_time': None, 'news': [], 'peers': []}}
        patcher = patch.object(ai_overview_page, 'get_page_snapshot', side_effect=snapshot)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_direct_and_rewritten_routes(self):
        self.assertEqual(route(handler('/ai-overview/IN:TCS')), 'ai-overview-page')
        self.assertEqual(route(handler('/api/index?route=ai-overview-page&symbol=IN:TCS')), 'ai-overview-page')
        self.assertEqual(route(handler('/api/index?route=ai-overview-page&symbol=IN:TCS', '/ai-overview/IN:TCS')), 'ai-overview-page')

    def test_page_is_public_and_symbol_is_escaped(self):
        request = handler('/ai-overview/IN:M%26M')
        ai_overview_page.handle_page(request)
        request.send_response.assert_called_with(200)
        body = request.wfile.getvalue()
        self.assertIn(b'data-symbol="IN:M&amp;M"', body)
        self.assertIn(b'https://www.mydailydigest.online/ai-overview/IN:M%26M', body)
        self.assertIn(b'href="/stocks/IN:M%26M"', body)
        self.assertIn(b'/ai-overview.js', body)
        self.assertIn(b'id="ai-insights"', body)

    def test_rewrite_symbol_and_invalid_symbols(self):
        request = handler('/api/index?route=ai-overview-page&symbol=IN:TCS')
        ai_overview_page.handle_page(request)
        request.send_response.assert_called_with(200)
        self.assertIn(b'data-symbol="IN:TCS"', request.wfile.getvalue())
        self.assertIn(b'Tata Consultancy Services (TCS) AI Overview', request.wfile.getvalue())
        self.assertIn(b'rel="canonical" href="https://www.mydailydigest.online/ai-overview/IN:TCS"', request.wfile.getvalue())

        for path in ['/ai-overview/US:AAPL', '/ai-overview/IN:..%2Fsecret']:
            request = handler(path)
            ai_overview_page.handle_page(request)
            request.send_response.assert_called_with(404)

    def test_original_path_identity_wins_over_query(self):
        request = handler('/api/index?route=ai-overview-page&symbol=IN:INFY', '/ai-overview/IN:TCS')
        ai_overview_page.handle_page(request)
        self.assertIn(b'data-symbol="IN:TCS"', request.wfile.getvalue())
        self.assertIn(b'Tata Consultancy Services (TCS) AI Overview', request.wfile.getvalue())
        self.assertIn(b'rel="canonical" href="https://www.mydailydigest.online/ai-overview/IN:TCS"', request.wfile.getvalue())


if __name__ == '__main__':
    unittest.main()
