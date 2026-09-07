import unittest

from test_ai_summary import sample_sections
from stock_news.render import build_email_digest, build_web_digest, build_web_section


class DigestDesignTest(unittest.TestCase):
    def test_email_without_ai_keeps_company_news_and_personal_links(self):
        html, text, _ = build_email_digest(
            sample_sections(), ['US:AAPL', 'US:MSFT'], 2, 'pre_open',
            digest_url='https://example.com/digest?t=signed-token',
            update_tickers_url='https://example.com/#update-tickers',
        )
        self.assertIn('Your opening briefing', html)
        self.assertNotIn('AI briefing · Your watchlist in context', html)
        self.assertIn('Apple expands services offering', html)
        self.assertIn('https://example.com/digest?t=signed-token', html)
        self.assertIn('https://example.com/#update-tickers', html)
        self.assertIn('$200.00', html)
        self.assertIn('+1.20% today', html)
        self.assertIn('$200.00  +1.20% today', text)

    def test_progressive_digest_keeps_loading_hooks_and_company_coverage(self):
        html = build_web_digest([], ['US:AAPL'], progressive=True, progressive_token='test-token')
        self.assertIn('id="digest-sections"', html)
        self.assertIn('data-token="test-token"', html)
        self.assertIn('id="progressive-ai"', html)
        self.assertIn('[hidden] { display: none !important; }', html)
        section = sample_sections()[0]
        section['web_stories'] = section['stories']
        fragment = build_web_section(section)
        self.assertIn('Company coverage', fragment)
        self.assertIn('$200.00', fragment)
        self.assertIn('https://example.com/apple', fragment)

    def test_watchlist_is_compact_wraps_and_keeps_unquoted_tickers(self):
        html = build_web_digest([], ['US:AAPL', 'IN:TCS'], progressive=True, progressive_token='test-token')

        self.assertIn('class="watchlist-count" aria-label="2 tickers">2</span>', html)
        self.assertRegex(html, r"\.movers-bar \.section-inner\s*\{[^}]*display:\s*grid;")
        self.assertRegex(html, r"\.movers-track\s*\{[^}]*flex-wrap:\s*wrap;")
        self.assertRegex(html, r"\.movers\s*\{[^}]*overflow:\s*visible;")
        self.assertIn("var movers = loaded.slice().sort", html)
        self.assertNotIn("loaded.filter(function (item) { return item.quote", html)

    def test_progressive_digest_sorts_rendered_sections_by_move_magnitude(self):
        html = build_web_digest([], ['US:AAPL', 'US:MSFT'], progressive=True, progressive_token='test-token')

        self.assertIn('setAttribute("data-move-magnitude", String(change))', html)
        self.assertIn("function sortTickerSectionsByMove()", html)
        self.assertIn("sortTickerSectionsByMove();", html)
