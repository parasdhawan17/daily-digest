# Phase 1 — Batch Market and Ticker AI Briefing

## Objective

Add an optional AI briefing to email digests while preserving the existing deterministic digest as the default and fallback path.

## Behavior

- After shared news collection and relevance filtering, split ticker summaries into bounded OpenRouter requests shared by the market/session.
- Use up to two selected stories per ticker and 12 tickers per request.
- Generate the shared headline and market context in one final synthesis request from successful batch themes.
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

- Limit each request with ticker, per-ticker story, concurrency, timeout, and output-token settings.
- Use strict JSON Schema output with every batch ticker required and additional ticker keys rejected.
- Use low temperature and bounded retries with exponential backoff.
- Instruct the model to treat article text as untrusted data and not follow embedded instructions.
- Do not send subscriber email addresses or full article bodies.
- The web page uses the same bounded batch pipeline and capped email-story input; it does not make per-section or per-story calls.

## Configuration

`OPENROUTER_API_KEY` enables the feature. The model, timeout, tickers per batch, stories per ticker, concurrency, retries, and output-token caps are configurable environment variables. The default is `google/gemini-2.5-flash-lite`, a low-cost text model, and is replaceable without code changes.

## Tests and acceptance

- Verify ticker batches are bounded and one final market synthesis is generated.
- Verify only exact requested tickers are accepted and rendered.
- Verify provider, malformed-response, and partial-batch failures degrade safely.
- Verify HTML and plain-text output include the AI section when valid output exists.
- Verify emails render unchanged when AI is disabled.
