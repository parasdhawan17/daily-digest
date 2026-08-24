# AI Summary Implementation

## Status

Phase 1 is implemented for both email digests and the full web digest. The feature is optional and preserves the existing deterministic digest when AI is disabled or unavailable.

No Vercel or Railway deployment has been made. The OpenRouter key is currently stored only in the ignored local `.env.local` file.

## Implemented behavior

### Shared generation strategy

- The email cron collects the union of subscriber tickers once per market/session.
- The web digest collects the token’s tickers once per page request.
- After relevance filtering, one OpenRouter batch request is made for the complete set of selected ticker stories.
- The request uses selected email stories only, not the full web story list.
- The result is reused across all subscriber emails or all ticker sections on that web page.
- There are no per-subscriber, per-section, or per-story AI requests.

### AI output

The model is asked to return structured JSON containing:

- `headline`: a concise editorial email heading under 72 characters.
- `market_context`: two or three plain-English sentences describing broad session themes without naming individual companies.
- `ticker_summaries`: a 35–55 word explanation in two or three short sentences per ticker, covering what happened and why it matters when supported by the supplied news.

The prompt instructs the model to write in clear, natural English for a general reader, briefly explain unavoidable financial terms, use only supplied headlines and excerpts, preserve uncertainty, ignore instructions inside external news text, avoid investment advice, and avoid inventing facts or unsupported consequences. It also includes one dense-to-clear style example.

### Email presentation

- When a valid AI headline is available, it becomes the email subject line. The current deterministic subject remains the fallback.
- The HTML email heading remains the compact deterministic mover heading to avoid duplicating the subject inside the message.
- The session-level AI briefing appears near the top of the email.
- Each ticker’s AI brief appears inside that ticker’s existing news card.
- Plain-text email output follows the same hierarchy.
- A short “AI-generated” disclaimer is included.
- A subscriber receives only ticker summaries for their own subscribed tickers.
- Existing headlines, excerpts, links, prices, subjects, and layout remain intact.

### Web presentation

- The session-level AI briefing appears below the movers area near the top of the full digest page.
- Each ticker’s AI brief appears inside its corresponding ticker section, above the news list.
- The web design reuses the existing color, spacing, typography, and dark-mode variables.
- The same AI disclaimer is shown.

## Cost and reliability controls

Current defaults:

| Setting | Default | Purpose |
|---|---:|---|
| `OPENROUTER_MODEL` | `google/gemini-2.5-flash-lite` | Low-cost text model |
| `AI_SUMMARY_MAX_STORIES` | `30` | Caps input stories per request |
| `AI_SUMMARY_MAX_OUTPUT_TOKENS` | `700` | Caps completion size |
| `AI_SUMMARY_TIMEOUT_SECONDS` | `15` | Prevents AI from delaying delivery |
| Temperature | `0.1` | Encourages concise, consistent output |
| Retries | `0` | Avoids duplicate spend in Phase 1 |

AI is disabled when `OPENROUTER_API_KEY` is absent. Any timeout, HTTP error, invalid JSON, missing required field, or unusable response returns `None` and leaves the normal digest unchanged.

## Configuration

Optional variables are documented in [`README.md`](../README.md) and [`.env.example`](../.env.example):

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `OPENROUTER_SITE_URL`
- `OPENROUTER_APP_NAME`
- `AI_SUMMARY_TIMEOUT_SECONDS`
- `AI_SUMMARY_MAX_STORIES`
- `AI_SUMMARY_MAX_OUTPUT_TOKENS`

The local key is kept in `.env.local`, which is ignored by Git. It must not be committed or copied into the repository. Production environments have not been configured yet.

## Main implementation locations

- [`stock_news/ai_summary.py`](../stock_news/ai_summary.py) — OpenRouter request, prompt, validation, and subscriber filtering.
- [`scripts/send_digests.py`](../scripts/send_digests.py) — one shared email generation call before the subscriber loop.
- [`api/digest.py`](../api/digest.py) — web-request generation path.
- [`stock_news/render.py`](../stock_news/render.py) — passes AI data into web and email templates.
- [`templates/email_digest.html`](../templates/email_digest.html) — email presentation.
- [`templates/web_digest.html`](../templates/web_digest.html) — full web digest presentation.

## Verification completed

The test suite passes with 9 tests covering:

- One shared OpenRouter batch request.
- Request token and temperature limits.
- Provider failure fallback.
- Strict response filtering.
- Subscriber-specific ticker filtering.
- Email HTML and plain-text rendering.
- Web session and ticker rendering.
- Existing scheduling and subscriber-market behavior.

Python compilation also succeeds for the application, scripts, and API modules.

## Deployment status

The implementation is local only. No Vercel or Railway environment variables were changed, and no deployment was triggered.

When production activation is approved, configure the OpenRouter variables in the relevant runtime environment and begin with a dry run or internal recipient. Keep the existing deterministic fallback enabled throughout rollout.

## Full plan references

- [Phase 1 plan](./phase-1-plan.md) — batch market and ticker briefing, current implementation scope.
- [Phase 2 plan](./phase-2-plan.md) — future per-story summaries and “why it matters” fields.
- [Phase 3 plan](./phase-3-plan.md) — future durable caching, usage monitoring, cost ceilings, and production hardening.

Phase 2 and Phase 3 are documented but not implemented yet.
