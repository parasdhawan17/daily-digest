# Phase 3 — AI Caching, Cost Controls, and Production Hardening

## Objective

Reduce repeated AI spending and add operational controls for reliable production use.

## Behavior

- Cache story summaries by a stable canonical story/content hash.
- Cache market briefings by a deterministic hash of the selected input and prompt version.
- Reuse cached results across subscribers and repeated digest runs where inputs are unchanged.
- Add configurable call, story, prompt-size, completion-size, timeout, and retry ceilings.
- Record model, latency, success/failure, token usage, cache status, and estimated cost without subscriber email addresses.
- Support an emergency configuration switch that disables AI immediately.
- Define provider routing and data-retention settings appropriate for supplied news data.

## Rollout

1. Dry-run generation without sending.
2. Send to an internal recipient.
3. Release to a small subscriber cohort.
4. Enable for all subscribers after monitoring quality, latency, and cost.

## Tests and acceptance

- Verify cache hits, misses, expiry, prompt-version changes, and story-content changes.
- Verify configured cost and call limits cannot be exceeded by one run.
- Verify provider failures, retries, and fallback routing remain non-fatal.
- Verify logs support cost and quality monitoring without leaking personal data.
- Verify disabling AI immediately restores the deterministic email path.
