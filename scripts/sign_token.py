#!/usr/bin/env python3
"""Generate a signed digest URL for local testing."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stock_news.tokens import build_digest_url, sign_digest_token


def main() -> None:
    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["AAPL", "MSFT"]
    try:
        url = build_digest_url(tickers)
        print(url)
    except Exception:
        token = sign_digest_token(tickers)
        print(f"/digest?t={token}")


if __name__ == "__main__":
    main()
