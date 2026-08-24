# Phase 2 — Per-Story AI Summaries

## Objective

Extend the Phase 1 batch response with concise summaries and “why it matters” text for individual selected stories.

## Behavior

- Keep one shared batch request per market/session.
- Summarize only stories already selected by the existing relevance and deduplication logic.
- Attach AI fields to existing story records without changing story URLs, identity, ordering, or source metadata.
- Render summaries beneath the corresponding headline in HTML and plain text.
- Keep the existing excerpt visible as fallback content.

## Validation and fallback

- Validate story IDs/ticker associations and enforce per-field character limits.
- Ignore incomplete or invalid individual AI results while keeping the story.
- Fall back to Phase 1 ticker summaries, then to the existing deterministic excerpts.
- Never present investment advice, unsupported facts, or fabricated citations.

## Tests and acceptance

- Test full, partial, duplicate, missing, and malformed story responses.
- Verify shared stories are summarized once for all subscribers.
- Verify links, ordering, and source metadata remain unchanged.
- Verify email previews with AI enabled and disabled.
