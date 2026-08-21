#!/usr/bin/env python3
"""Send personalized stock digest emails to Brevo subscribers."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_env_file(path: Path, *, override: bool = False) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        if key in os.environ and not override:
            continue
        os.environ[key] = value


def load_env_files() -> None:
    sibling_bot_env = ROOT.parent / "stock-news-bot" / ".env"
    for path in (sibling_bot_env, ROOT / ".env"):
        _load_env_file(path)
    _load_env_file(ROOT / ".env.local", override=True)


load_env_files()

from stock_news.brevo import BrevoError, fetch_subscribers_with_tickers, send_transactional_email
from stock_news.config import (
    BREVO_API_KEY,
    BREVO_LIST_ID,
    EMAIL_FROM,
    EMAIL_FROM_NAME,
    FINNHUB_KEY,
    SITE_URL,
)
from stock_news.digest import collect_digest_data, filter_sections
from stock_news.email import count_email_stories, digest_session, scheduled_send_at_iso, union_tickers
from stock_news.market_calendar import trading_day_skip_reason
from stock_news.render import build_email_digest
from stock_news.tokens import build_digest_url


def require_env(name: str, value: str | None) -> str:
    if not value:
        print(f"Error: missing required environment variable {name}", file=sys.stderr)
        sys.exit(1)
    return value


def email_configured() -> bool:
    return bool(BREVO_API_KEY and EMAIL_FROM and BREVO_LIST_ID)


def missing_email_env() -> list[str]:
    missing: list[str] = []
    if not os.environ.get("FINNHUB_API_KEY", "").strip():
        missing.append("FINNHUB_API_KEY")
    if not os.environ.get("BREVO_API_KEY", "").strip():
        missing.append("BREVO_API_KEY")
    if not os.environ.get("EMAIL_FROM", "").strip():
        missing.append("EMAIL_FROM")
    if not os.environ.get("DIGEST_SIGNING_SECRET", "").strip():
        missing.append("DIGEST_SIGNING_SECRET")
    if not os.environ.get("SITE_URL", "").strip():
        missing.append("SITE_URL")
    return missing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch stock news and send personalized digest emails via Brevo.",
    )
    parser.add_argument(
        "--email",
        action="store_true",
        help="Send the HTML email digest via Brevo.",
    )
    parser.add_argument(
        "--session",
        choices=("auto", "pre_open", "post_close"),
        default="auto",
        help=(
            "Email subject style: pre_open uses multi-headline teasers, "
            "post_close uses multi-mover chips. Default auto uses America/New_York clock."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build digests and print subjects without sending email.",
    )
    parser.add_argument(
        "--recipient",
        metavar="EMAIL",
        help="Only prepare/send email for this subscriber address (case-insensitive).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Send even on weekends or market holidays (manual testing).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.email:
        print("Error: pass --email to send digest emails.", file=sys.stderr)
        sys.exit(1)

    missing = missing_email_env()
    if missing:
        print(
            "Email env not configured yet — skipping send. "
            f"Set in Railway Variables: {', '.join(missing)}",
        )
        return

    recipient_filter = (args.recipient or "").strip().lower() or None
    dry_run = args.dry_run
    email_session = digest_session(override=args.session)

    if not email_configured():
        print(
            "Error: BREVO_API_KEY, EMAIL_FROM, and BREVO_LIST_ID are required.",
            file=sys.stderr,
        )
        sys.exit(1)

    finnhub_key = require_env("FINNHUB_API_KEY", FINNHUB_KEY)
    brevo_key = require_env("BREVO_API_KEY", BREVO_API_KEY)
    list_id = int(require_env("BREVO_LIST_ID", BREVO_LIST_ID))
    sender_email = require_env("EMAIL_FROM", EMAIL_FROM)
    site_url = require_env("SITE_URL", os.environ.get("SITE_URL", "").rstrip("/"))
    signing_secret = require_env(
        "DIGEST_SIGNING_SECRET",
        os.environ.get("DIGEST_SIGNING_SECRET", "").strip(),
    )
    if signing_secret in ("[SENSITIVE]", "test-secret-for-dry-run") or len(signing_secret) < 32:
        print(
            "Error: DIGEST_SIGNING_SECRET looks invalid. "
            "Use a real secret from .env.local (vercel env pull only returns [SENSITIVE]).",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.force:
        skip = trading_day_skip_reason(api_key=finnhub_key)
        if skip:
            print(f"Not a US trading day (ET) — skipping digest send ({skip}).")
            return

    subscribers = fetch_subscribers_with_tickers(list_id, brevo_key)
    print(f"Fetched {len(subscribers)} subscriber(s) from Brevo list {list_id}")

    if recipient_filter:
        matched = [
            s for s in subscribers if s.get("email", "").strip().lower() == recipient_filter
        ]
        if not matched:
            print(f"No subscriber matched --recipient {args.recipient}", file=sys.stderr)
            sys.exit(1)
        subscribers = matched
        print(f"Filtered to recipient: {subscribers[0]['email']}")

    if not subscribers:
        print("No email recipients found; nothing to send.")
        return

    digest_tickers = union_tickers(subscribers)
    if not digest_tickers:
        print("No valid tickers across subscribers; nothing to send.")
        return

    print(f"Fetching digest data for {len(digest_tickers)} ticker(s): {', '.join(digest_tickers)}")
    sections, _ = collect_digest_data(digest_tickers, finnhub_key)

    print(f"Email subject session: {email_session}")
    scheduled_at = scheduled_send_at_iso(email_session)
    if scheduled_at:
        print(f"Scheduling Brevo delivery at {scheduled_at}")
    else:
        print("Sending immediately (no scheduledAt).")
    if dry_run:
        print("Email dry-run: subjects and digest URLs will be printed, nothing sent.")

    update_tickers_url = f"{site_url.rstrip('/')}/#update-tickers"
    sent_count = 0

    for subscriber in subscribers:
        email = subscriber["email"]
        user_tickers = subscriber["tickers"]
        if not user_tickers:
            print(f"Skipped {email}: no valid tickers")
            continue

        user_sections = filter_sections(sections, user_tickers)
        user_story_count = count_email_stories(user_sections)
        digest_url = build_digest_url(user_tickers, site_url=site_url)
        html, text, subject = build_email_digest(
            user_sections,
            user_tickers,
            user_story_count,
            email_session,
            digest_url=digest_url,
            update_tickers_url=update_tickers_url,
        )
        print(
            f"Prepared email for {email} "
            f"({len(user_tickers)} tickers, subject: {subject})"
        )
        if dry_run:
            print(f"Dry-run digest URL: {digest_url}")
            print(f"Dry-run subject [{email_session}]: {subject}")
            print(f"Dry-run HTML size: {len(html)} chars")
            sent_count += 1
            continue

        try:
            send_transactional_email(
                html,
                text,
                brevo_key,
                sender_email,
                [email],
                EMAIL_FROM_NAME,
                subject,
                scheduled_at=scheduled_at,
            )
            sent_count += 1
        except BrevoError as exc:
            print(f"Failed to send to {email}: {exc}", file=sys.stderr)

    print(f"Done. {'Would send' if dry_run else 'Sent'} {sent_count} email(s).")


if __name__ == "__main__":
    main()
