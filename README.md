# Daily Digest

Live web app for **Daily Digest** — marketing landing page plus on-demand personalized stock news digests on Vercel.

Email delivery stays in the separate [stock-news-bot](https://github.com/parasdhawan17/stock-news-bot) repository.

## What this repo contains

| Path | Purpose |
|------|---------|
| `public/` | Static landing page (`/`) |
| `api/digest.py` | Vercel serverless — live digest (`/digest?t=...`) |
| `stock_news/` | Python package (Finnhub fetch, relevance, render, tokens) |
| `templates/` | Jinja HTML templates |
| `documents/` | Product requirements, technical spec, implementation plan |

## Quick start (local)

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in keys
npx vercel dev         # or: vercel dev
```

- Landing: http://localhost:3000/
- Digest: http://localhost:3000/digest?t=<signed_token>

## Deploy (Vercel)

1. Import this repo at [vercel.com/new](https://vercel.com/new).
2. Project name: **Daily Digest**.
3. Production branch: `main`.
4. Set environment variables (see `.env.example`).
5. Add custom domain; set `SITE_URL` to match.

Deploys automatically on every push to `main` via the Vercel GitHub app.

## Related repos

- **Email bot:** [parasdhawan17/stock-news-bot](https://github.com/parasdhawan17/stock-news-bot)
- **Signing secret:** `DIGEST_SIGNING_SECRET` must match between GitHub Actions (email) and Vercel (digest verify).

## Docs

- [Product requirements](documents/product-requirements.md)
- [Technical implementation](documents/technical-implementation.md)
- [Implementation plan](documents/implementation-plan.md)
