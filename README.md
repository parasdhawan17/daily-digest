# Daily Digest

Live web app for **Daily Digest** — marketing landing page plus on-demand personalized stock news digests on Vercel.

Email delivery stays in the separate [stock-news-bot](https://github.com/parasdhawan17/stock-news-bot) repository.

## What this repo contains

| Path | Purpose |
|------|---------|
| `public/` | Static landing page (`/`) |
| `api/digest.py` | Vercel serverless — live digest (`/digest?t=...`) |
| `api/tickers_search.py` | Ticker autocomplete (Finnhub search) |
| `api/subscribe.py` | Subscribe / update holdings (Brevo API) |
| `stock_news/` | Python package (Finnhub fetch, relevance, render, tokens) |
| `templates/` | Jinja HTML templates |
| `documents/` | Product requirements, technical spec, implementation plan |

## Quick start (local)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./scripts/dev.sh              # or: .venv/bin/python3 scripts/dev_server.py
```

- Landing: http://localhost:3000/
- Digest: http://localhost:3000/digest?t=<signed_token>

## Deploy (Vercel)

1. Import this repo at [vercel.com/new](https://vercel.com/new).
2. Project name: **Daily Digest**.
3. Production branch: `main`.
4. Set environment variables (see below).
5. Add custom domain; set `SITE_URL` to match.

### Environment variables (Vercel)

| Variable | Required for | Notes |
|----------|--------------|-------|
| `FINNHUB_API_KEY` | Digest + ticker search/validation | Same key as stock-news-bot |
| `DIGEST_SIGNING_SECRET` | Signed digest links | Must match stock-news-bot |
| `SITE_URL` | Digest links + Brevo DOI redirect | e.g. `https://yourdomain.com` |
| `BREVO_API_KEY` | Subscribe form | Same key as stock-news-bot |
| `BREVO_LIST_ID` | Subscribe form | Brevo list ID |
| `BREVO_DOI_TEMPLATE_ID` | New subscribers | Double opt-in template ID from Brevo (same template as your old embedded form) |

Copy from sibling `stock-news-bot/.env` via `./scripts/setup_vercel_env.sh`.

**Finding `BREVO_DOI_TEMPLATE_ID`:** In Brevo, open the double opt-in email template used for your subscribe form → Settings → template ID (numeric).

Deploys automatically on every push to `main` via the Vercel GitHub app.

## Related repos

- **Email bot:** [parasdhawan17/stock-news-bot](https://github.com/parasdhawan17/stock-news-bot)
- **Signing secret:** `DIGEST_SIGNING_SECRET` must match between GitHub Actions (email) and Vercel (digest verify).

## Docs

- [Product requirements](documents/product-requirements.md)
- [Technical implementation](documents/technical-implementation.md)
- [Implementation plan](documents/implementation-plan.md)
