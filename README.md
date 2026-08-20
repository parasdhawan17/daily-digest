# Daily Digest

Live web app for **Daily Digest** — marketing landing page plus on-demand personalized stock news digests on Vercel. Twice-daily email digests run on Railway cron.

## What this repo contains

| Path | Purpose |
|------|---------|
| `public/` | Static landing page (`/`) |
| `api/digest.py` | Vercel serverless — live digest (`/digest?t=...`) |
| `api/tickers_search.py` | Ticker autocomplete (Finnhub search) |
| `api/subscribe.py` | Subscribe / update holdings (Brevo API) |
| `scripts/send_digests.py` | Email cron entrypoint (Railway) |
| `stock_news/` | Python package (Finnhub fetch, relevance, render, tokens) |
| `templates/` | Jinja HTML templates (web + email) |
| `railway.toml` | Railway cron schedule and start command |
| `documents/` | Product requirements, technical spec, implementation plan |

## Quick start (local)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./scripts/dev.sh              # or: .venv/bin/python3 scripts/dev_server.py
```

- Landing: http://localhost:3000/
- Digest: http://localhost:3000/digest?t=<signed_token>

### Email dry-run (local)

```bash
# Copy env from stock-news-bot/.env or set variables manually
.venv/bin/python scripts/send_digests.py --email --dry-run
.venv/bin/python scripts/send_digests.py --email --dry-run --recipient you@example.com
```

## Deploy (Vercel)

1. Import this repo at [vercel.com/new](https://vercel.com/new).
2. Project name: **Daily Digest**.
3. Production branch: `main`.
4. Set environment variables (see below).
5. Add custom domain (`www.mydailydigest.online`); set `SITE_URL` to `https://www.mydailydigest.online`.

### Environment variables (Vercel)

| Variable | Required for | Notes |
|----------|--------------|-------|
| `FINNHUB_API_KEY` | Digest + ticker search/validation | |
| `DIGEST_SIGNING_SECRET` | Signed digest links | Must match Railway cron service |
| `SITE_URL` | Digest links + Brevo DOI redirect | `https://www.mydailydigest.online` |
| `BREVO_API_KEY` | Subscribe form | |
| `BREVO_LIST_ID` | Subscribe form | Always `7` (Daily Digest - US). Setup scripts pin this. |
| `BREVO_DOI_TEMPLATE_ID` | New subscribers | Double opt-in template ID from Brevo |
| `BREVO_TICKERS_ATTRIBUTE` | Subscribe + email cron | Optional (default `US_TICKERS` — text, comma-separated) |

Copy from sibling `stock-news-bot/.env` via `./scripts/setup_vercel_env.sh`.

**Finding `BREVO_DOI_TEMPLATE_ID`:** In Brevo, open the double opt-in email template used for your subscribe form → Settings → template ID (numeric).

Deploys automatically on every push to `main` via the Vercel GitHub app.

## Email cron (Railway)

Production email digests run on a **separate Railway cron service** connected to this repo (not Vercel).

1. Create a Railway project (e.g. **daily-digest-cron**).
2. Connect the `daily-digest` GitHub repo as a new service.
3. In Railway **Settings** (not `railway.toml` — set cron in the UI):
   - **Cron Schedule:** `15 13,20 * * *` UTC (~9:15 AM and 4:15 PM ET during EDT)
   - **Start Command:** `python scripts/send_digests.py --email`
   - **Restart Policy:** Never
4. Set environment variables on the Railway service:

| Variable | Required |
|----------|----------|
| `FINNHUB_API_KEY` | Yes |
| `BREVO_API_KEY` | Yes |
| `BREVO_LIST_ID` | Yes — `7` |
| `EMAIL_FROM` | Yes |
| `EMAIL_FROM_NAME` | Yes |
| `DIGEST_SIGNING_SECRET` | Yes — must match Vercel |
| `SITE_URL` | Yes — `https://www.mydailydigest.online` |
| `TZ` | `America/New_York` (recommended) |
| `BREVO_TICKERS_ATTRIBUTE` | Optional (default `US_TICKERS`) |

5. Trigger a manual deploy in Railway to verify logs before the first scheduled run.

Or run `./scripts/setup_railway_env.sh` after `npx @railway/cli login` and `railway link`.

Each email includes a signed **See the full digest online** link (`/digest?t=...`) personalized to that subscriber's tickers. The web digest loads live from Finnhub when clicked.

## Related repos

- **Legacy bot:** [parasdhawan17/stock-news-bot](https://github.com/parasdhawan17/stock-news-bot) — GitHub Actions schedule disabled; manual `workflow_dispatch` only for emergencies.

## Docs

- [Product requirements](documents/product-requirements.md)
- [Technical implementation](documents/technical-implementation.md)
- [Implementation plan](documents/implementation-plan.md)
