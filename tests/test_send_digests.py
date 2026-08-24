import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts.send_digests import send_for_market


class MarketDigestLinkTest(unittest.TestCase):
    @patch("scripts.send_digests.build_email_digest", return_value=("html", "text", "subject"))
    @patch("scripts.send_digests.build_digest_url", return_value="https://example.com/digest?t=token")
    @patch("scripts.send_digests.generate_ai_summary", return_value=None)
    @patch("scripts.send_digests.collect_digest_data")
    @patch("scripts.send_digests.fetch_subscribers_with_tickers")
    def test_email_link_contains_only_current_market_tickers(
        self,
        fetch_subscribers,
        collect_digest_data,
        _generate_ai_summary,
        build_digest_url,
        _build_email_digest,
    ) -> None:
        args = SimpleNamespace(force=True, recipient=None, dry_run=True)
        cases = (
            ("IN", ["IN:RELIANCE", "IN:TCS"]),
            ("US", ["US:AAPL"]),
        )
        for market, expected_tickers in cases:
            with self.subTest(market=market):
                fetch_subscribers.return_value = [
                    {
                        "email": "both@example.com",
                        "tickers": ["US:AAPL", "IN:RELIANCE", "IN:TCS"],
                    }
                ]
                collect_digest_data.return_value = (
                    [{"ticker": ticker, "stories": []} for ticker in expected_tickers],
                    None,
                )

                sent = send_for_market(
                    market,
                    "pre_open",
                    args=args,
                    finnhub_key="finnhub-key",
                    indianapi_key="india-key",
                    brevo_key="brevo-key",
                    list_id=1,
                    sender_email="sender@example.com",
                    site_url="https://example.com",
                    signing_secret="unused",
                )

                self.assertEqual(sent, 1)
                build_digest_url.assert_called_once_with(
                    expected_tickers,
                    site_url="https://example.com",
                )
                build_digest_url.reset_mock()


if __name__ == "__main__":
    unittest.main()
