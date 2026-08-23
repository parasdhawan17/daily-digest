import unittest
from datetime import datetime, timezone

from stock_news.email import cron_sessions, subscribers_for_market


class CronSessionsTest(unittest.TestCase):
    def test_india_sessions_use_ist(self) -> None:
        self.assertEqual(
            cron_sessions(datetime(2026, 8, 24, 3, 45, tzinfo=timezone.utc)),
            [("IN", "pre_open")],
        )
        self.assertEqual(
            cron_sessions(datetime(2026, 8, 24, 10, 15, tzinfo=timezone.utc)),
            [("IN", "post_close")],
        )

    def test_us_sessions_follow_daylight_saving(self) -> None:
        self.assertEqual(
            cron_sessions(datetime(2026, 8, 24, 13, 15, tzinfo=timezone.utc)),
            [("US", "pre_open")],
        )
        self.assertEqual(
            cron_sessions(datetime(2026, 1, 5, 14, 15, tzinfo=timezone.utc)),
            [("US", "pre_open")],
        )
        self.assertEqual(
            cron_sessions(datetime(2026, 8, 24, 20, 15, tzinfo=timezone.utc)),
            [("US", "post_close")],
        )
        self.assertEqual(
            cron_sessions(datetime(2026, 1, 5, 21, 15, tzinfo=timezone.utc)),
            [("US", "post_close")],
        )

    def test_non_session_candidate_does_not_run(self) -> None:
        self.assertEqual(
            cron_sessions(datetime(2026, 8, 24, 14, 15, tzinfo=timezone.utc)),
            [],
        )


class MarketSubscriberTest(unittest.TestCase):
    def test_filters_tickers_and_recipients_by_market(self) -> None:
        subscribers = [
            {"email": "both@example.com", "tickers": ["US:AAPL", "IN:RELIANCE"]},
            {"email": "us@example.com", "tickers": ["US:MSFT"]},
            {"email": "in@example.com", "tickers": ["IN:TCS"]},
        ]

        self.assertEqual(
            subscribers_for_market(subscribers, "IN"),
            [
                {"email": "both@example.com", "tickers": ["IN:RELIANCE"]},
                {"email": "in@example.com", "tickers": ["IN:TCS"]},
            ],
        )
        self.assertEqual(
            subscribers_for_market(subscribers, "US"),
            [
                {"email": "both@example.com", "tickers": ["US:AAPL"]},
                {"email": "us@example.com", "tickers": ["US:MSFT"]},
            ],
        )


if __name__ == "__main__":
    unittest.main()
