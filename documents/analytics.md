# Website analytics

Tickr Digest uses PostHog when `POSTHOG_PROJECT_KEY` is configured. The shared
client is `public/analytics.js`; `/api/analytics/config` supplies its public
project key and regional ingestion host.

## Event taxonomy

All manual events include `schema_version`, `page_type`, `page_path`, `viewport`,
and the public stock `symbol` when the page has one.

| Event | Purpose | Useful properties |
|---|---|---|
| `$pageview` | Visitors and page popularity | `page_type`, `referrer_host`, `viewport` |
| `section_viewed` | Which visible page areas people reach | `section`, `section_ticker` |
| `feature_used` | Deliberate product interactions | `feature`, `action`, `section`, `category`, `card` |
| `api_request_completed` | User-visible API reliability and latency | `endpoint`, `status_group`, `success`, `duration_ms` |
| `ai_request_completed` | AI adoption, success rate, and latency | `feature`, `success`, `duration_ms`, `status` |
| `app_error` | Uncaught browser failures | `source`, `error_type`, `error_message` |
| `$exception` | PostHog Error Tracking issue grouping | Captured alongside `app_error` when supported by the SDK |

Signed-in users receive a stable SHA-256 identifier derived from the provider
subject. Email addresses are never used as analytics identities or properties.

## Recommended PostHog dashboard

1. Unique visitors: unique users on `$pageview`, broken down by `page_type`.
2. Most-used features: unique users on `feature_used`, broken down by `feature`.
3. Most-viewed content: unique users on `section_viewed`, broken down by
   `section`, with separate filters for `page_type`.
4. AI adoption: unique users on `ai_request_completed`, broken down by `feature`.
5. AI success: percentage of `ai_request_completed` where `success = true`.
6. Reliability: failed `api_request_completed` events by `endpoint` and
   `status_group`, plus `app_error` and `$exception` trends.
7. Performance: p50 and p95 `duration_ms` for `api_request_completed` and
   `ai_request_completed`.

## Privacy boundaries

Autocapture is disabled. Form values, search queries, email addresses, request
bodies, AI prompts and responses, digest tokens, and URL query strings are not
sent as event properties. Session replay masks input, textarea, editable, and
`data-private` content. Error text redacts common email, credential, token,
prompt, and signed-token patterns before capture.
