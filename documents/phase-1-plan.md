# Phase 1 — Batch Market and Ticker AI Briefing

## Objective

Add an optional AI briefing to email digests while preserving the existing deterministic digest as the default and fallback path.

## Behavior

- After shared news collection and relevance filtering, make at most one OpenRouter request per market/session.
- Provide the model with selected headlines, short excerpts, sources, timestamps, and ticker IDs only.
- Request JSON containing a broad market context and one concise summary per ticker.
- Request one validated editorial headline for the email subject; keep the existing deterministic subject as fallback.
- Keep the HTML email heading compact and deterministic to avoid duplicating the subject.
- Filter ticker summaries per subscriber before rendering so subscribers see only their own tickers.
- Render the AI section in both HTML and plain-text email formats.
- Render the session context at the top of the full web digest and the matching ticker brief inside each web ticker section.
- Disable the feature automatically when `OPENROUTER_API_KEY` is absent.
- Treat timeouts, provider errors, malformed JSON, missing fields, and empty output as non-fatal.

## Cost and safety controls

- Limit input to `AI_SUMMARY_MAX_STORIES` stories.
- Limit output with `AI_SUMMARY_MAX_OUTPUT_TOKENS`.
- Use low temperature and no retries in Phase 1.
- Instruct the model to treat article text as untrusted data and not follow embedded instructions.
- Do not send subscriber email addresses or full article bodies.
- The web page uses the same single batch call and capped email-story input; it does not make per-section or per-story calls.

## Configuration

`OPENROUTER_API_KEY` enables the feature. `OPENROUTER_MODEL`, timeout, story cap, and output-token cap are configurable environment variables. The default is `google/gemini-2.5-flash-lite`, a low-cost text model, and is replaceable without code changes.

## Tests and acceptance

- Verify one request for a shared market run.
- Verify only exact requested tickers are accepted and rendered.
- Verify provider failure and malformed responses return the normal digest.
- Verify HTML and plain-text output include the AI section when valid output exists.
- Verify emails render unchanged when AI is disabled.
