import unittest
from types import SimpleNamespace
from unittest.mock import patch

from api.digest import handle_subscription_get
from stock_news.tokens import DigestTokenClaims


class SubscriptionPrefillHandlerTest(unittest.TestCase):
    @patch("api.digest.send_json")
    @patch("api.digest.verify_digest_claims")
    def test_old_link_falls_back_to_digest_tickers(self, verify_claims, send_json) -> None:
        verify_claims.return_value = DigestTokenClaims(["US:AAPL"])
        handler = SimpleNamespace(path="/api/subscription?t=old-token")

        handle_subscription_get(handler)

        send_json.assert_called_once_with(
            handler,
            200,
            {"ok": True, "email": "", "tickers": ["US:AAPL"]},
        )

    @patch.dict("os.environ", {"BREVO_API_KEY": "brevo-key"})
    @patch("api.digest.send_json")
    @patch("api.digest.get_contact")
    @patch("api.digest.verify_digest_claims")
    def test_new_link_returns_current_full_subscription(
        self,
        verify_claims,
        get_contact,
        send_json,
    ) -> None:
        verify_claims.return_value = DigestTokenClaims(["US:AAPL"], subscriber_id=42)
        get_contact.return_value = {
            "email": "Investor@Example.com",
            "attributes": {"US_TICKERS": "US:AAPL, IN:TCS"},
        }
        handler = SimpleNamespace(path="/api/subscription?t=new-token")

        handle_subscription_get(handler)

        get_contact.assert_called_once_with(42, "brevo-key")
        send_json.assert_called_once_with(
            handler,
            200,
            {
                "ok": True,
                "email": "investor@example.com",
                "tickers": ["US:AAPL", "IN:TCS"],
            },
        )


if __name__ == "__main__":
    unittest.main()
