
# Daily Digest — plan index

**Project name:** Daily Digest  
**New repository:** [`daily-digest`](https://github.com/parasdhawan17/daily-digest)  
**Email repository (unchanged):** [`stock-news-bot`](https://github.com/parasdhawan17/stock-news-bot)  
**Vercel:** Import `daily-digest` repo; display name **Daily Digest**; auto-deploy on push to `main`.

Planning docs:

| Document | Purpose |
|----------|---------|
| [product-requirements.md](product-requirements.md) | **What** — personas, requirements, acceptance |
| [technical-implementation.md](technical-implementation.md) | **How** — two-repo architecture, Vercel, tokens, phases |

## Quick summary

- **daily-digest:** Vercel `public/` landing + `/digest?t=...` live serverless digest.
- **stock-news-bot:** GitHub Actions 2× daily → Brevo emails with signed links to Daily Digest.
- **Deploy:** Vercel Git integration on `daily-digest` (no Actions deploy workflow).
- **Cost:** $0 hosting + domain ~$10–15/year.

## Implementation phases

See [technical-implementation.md](technical-implementation.md) Section 11.

0. Create `daily-digest` GitHub repo + scaffold  
1. `stock_news/` package in `daily-digest`  
2. Vercel skeleton (landing + API)  
3. Email link integration in `stock-news-bot` only  
4. Vercel production + custom domain  
5. Hardening + cleanup  

## Launch checklist

See [product-requirements.md](product-requirements.md) Section 13.
