import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from test_ai_summary import sample_sections
from stock_news.design import resolve_design, design_url, design_for_recipient
from stock_news.render import build_email_digest, build_web_digest, build_web_section


class DesignVariantsTest(unittest.TestCase):
    def test_flag_default_override_and_allowlist(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_design(), 'modern')
        with patch.dict(os.environ, {'DIGEST_DESIGN': 'legacy'}):
            self.assertEqual(resolve_design(), 'legacy')
            self.assertEqual(resolve_design('modern'), 'modern')
            self.assertEqual(resolve_design('../../other'), 'legacy')
        with patch.dict(os.environ, {'DIGEST_DESIGN': 'typo'}):
            with self.assertRaises(ValueError):
                resolve_design()

    def test_url_retains_token_and_fragment_and_replaces_variant(self):
        url = design_url('https://example.com/digest?t=abc.def&design=modern#stock', 'legacy')
        parts = urlsplit(url)
        self.assertEqual(parse_qs(parts.query), {'t': ['abc.def'], 'design': ['legacy']})
        self.assertEqual(parts.fragment, 'stock')
        self.assertIsNone(design_url(None, 'legacy'))

    def test_both_email_presentations_keep_data_and_pin_links(self):
        for variant in ('legacy', 'modern'):
            with self.subTest(variant=variant):
                html, text, _ = build_email_digest(
                    sample_sections(), ['US:AAPL', 'US:MSFT'], 2, 'post_close',
                    digest_url='https://example.com/digest?t=signed', design=variant,
                )
                self.assertIn('Apple expands services offering', html)
                self.assertIn('design=' + variant, html)
                self.assertIn('design=' + variant, text)
                self.assertEqual('$200.00' in html, variant == 'legacy')
                self.assertEqual('$200.00' in text, variant == 'legacy')

    def test_shell_and_fragment_use_same_variant(self):
        section = sample_sections()[0]
        section['web_stories'] = section['stories']
        for variant in ('legacy', 'modern'):
            with self.subTest(variant=variant):
                html = build_web_digest([], ['US:AAPL'], progressive=True, progressive_token='signed', design=variant)
                self.assertIn('/api/digest-data?design=' + variant + '&t=', html)
                self.assertEqual('Your stocks. The bigger picture.' in html, variant == 'modern')
                fragment = build_web_section(section, design=variant)
                self.assertEqual('Company coverage' in fragment, variant == 'modern')
                self.assertIn('$200.00', fragment)

    def test_targeted_recipient_override_wins_over_legacy_default(self):
        with patch.dict(os.environ, {'DIGEST_DESIGN': 'legacy'}):
            self.assertEqual(design_for_recipient(' paras.dhawan17@GMAIL.COM '), 'modern')
            self.assertEqual(design_for_recipient('someone-else@example.com'), 'legacy')
