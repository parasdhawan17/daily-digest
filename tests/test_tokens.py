import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from stock_news.tokens import (
    build_digest_url,
    sign_digest_token,
    verify_digest_claims,
    verify_digest_token,
)


class DigestTokenClaimsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {"DIGEST_SIGNING_SECRET": "test-secret"})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()

    def test_subscriber_id_round_trips_without_changing_ticker_api(self) -> None:
        token = sign_digest_token(["US:AAPL", "IN:TCS"], subscriber_id=42)

        claims = verify_digest_claims(token)

        self.assertEqual(claims.tickers, ["US:AAPL", "IN:TCS"])
        self.assertEqual(claims.subscriber_id, 42)
        self.assertEqual(verify_digest_token(token), claims.tickers)

    def test_old_tokens_without_subscriber_id_remain_valid(self) -> None:
        token = sign_digest_token(["US:MSFT"])

        claims = verify_digest_claims(token)

        self.assertEqual(claims.tickers, ["US:MSFT"])
        self.assertIsNone(claims.subscriber_id)

    def test_digest_url_can_include_subscriber_claim(self) -> None:
        url = build_digest_url(
            ["US:NVDA"],
            site_url="https://example.com",
            subscriber_id=7,
        )
        token = parse_qs(urlparse(url).query)["t"][0]

        self.assertEqual(verify_digest_claims(token).subscriber_id, 7)


if __name__ == "__main__":
    unittest.main()
