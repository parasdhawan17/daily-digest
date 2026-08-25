# Paid Subscription Plan for Daily Digest

## Summary

Convert Daily Digest from a Brevo-managed free mailing list into an entitlement-based paid service:

- India-only launch using Razorpay Subscriptions.
- Two calendar months free after mandate authorization, followed by ₹100/month total, including applicable tax.
- Recurring mandate collected during signup through card, UPI AutoPay, or eMandate.
- Passwordless account management through email magic links.
- Existing subscribers receive a fresh two-month trial after authorizing payment and a 30-day migration window.
- Managed PostgreSQL becomes the source of truth; Brevo remains the email delivery provider.
- Landing pages remain public, while digest emails and web digests require a valid trial, paid period, legacy migration period, or payment-failure grace period.

Razorpay supports future subscription start dates for trials, INR recurring payment methods, and subscription lifecycle webhooks. [Razorpay trial setup](https://razorpay.com/docs/payments/subscriptions/create/), [supported payment methods](https://razorpay.com/docs/payments/subscriptions/supported-payment-methods/), [webhook events](https://razorpay.com/docs/payments/subscriptions/subscribe-to-webhooks/).

## Product and Billing Rules

- Create one Razorpay monthly plan for `INR 10000` paise and one unit per customer.
- The advertised and final recurring charge is exactly ₹100. If GST applies, derive the taxable value and tax component from this tax-inclusive total.
- Calculate the first billing timestamp as checkout creation plus two calendar months, using end-of-month clamping. Store timestamps in UTC and display dates in IST.
- A trial starts only after:
  1. The email is verified.
  2. Razorpay confirms the recurring mandate/authentication.
- A small refundable authorization transaction may appear if Razorpay requires it; disclose this before checkout without promising a fixed authorization amount.
- Allow one lifetime trial per normalized email. Where Razorpay exposes stable, non-sensitive customer identifiers, use them as a secondary abuse signal; never store card, bank, or UPI credentials.
- Re-subscription after a used trial starts billing immediately or at the end of remaining prepaid access, whichever prevents overlapping charges.
- Active cancellation takes effect at the end of the paid billing period. Trial cancellation cancels the provider mandate immediately but retains local access until the displayed trial end.
- Failed renewal enters a three-day grace period. Successful retry restores normal access; after grace expiry, emails and web-digest access stop.
- No prorated refunds. Support may refund duplicate, erroneous, legally required, or approved exceptional charges. Refunds must record reason, operator, provider refund ID, and whether access should be revoked.
- Do not offer pause, coupons, family plans, multiple paid tiers, international billing, or alternative currencies in v1.

## Architecture, Data, and Interfaces

### Persistent platform

- Add managed PostgreSQL, preferably Neon’s pooled PostgreSQL integration shared by Vercel and Railway.
- Use versioned SQL migrations and lightweight `psycopg` repositories rather than introducing a full ORM.
- Make the database authoritative for users, watchlists, consent, billing status, and email eligibility. Brevo contacts are no longer used to decide who receives a digest.

Core records:

- `customers`: UUID, normalized unique email, verification timestamp, optional name/phone, Brevo contact ID, trial-used flag, legacy-access deadline, email-delivery status, created/updated timestamps.
- `watchlists`: customer ID, validated ticker JSON, version, updated timestamp.
- `subscriptions`: customer ID, Razorpay customer/subscription/plan IDs, exact provider status, trial dates, billing-period dates, grace deadline, access deadline, cancellation state, last provider event timestamp.
- `payments`: unique payment/invoice/refund IDs, amount, currency, state, billing period, paid/refunded timestamps, tax metadata.
- `webhook_events`: unique Razorpay event ID, event type, receipt/processing status, selected provider metadata, error information.
- `auth_tokens` and `sessions`: hashed single-use magic-link tokens, purpose, expiry, use timestamp, revocable session IDs, and CSRF secret.
- `consents` and `audit_log`: terms/privacy versions, timestamps, signup source, billing/cancellation/refund/admin actions.
- `email_outbox`: idempotent lifecycle email jobs and delivery attempts.

Keep Razorpay’s provider status separate from derived access status:

- Provider: `created`, `authenticated`, `active`, `pending`, `halted`, `cancelled`, `completed`, or `paused`.
- Access: `pending`, `legacy`, `trialing`, `active`, `grace`, or `expired`.
- Centralize eligibility in one function used by the web digest, email cron, account page, and support tooling.

### Public flows and endpoints

Extend the unified Vercel router and add:

- `POST /api/signup`: validate email/tickers, rate-limit, record current legal consent, send verification link, and always return a non-enumerating response.
- `GET /verify-email?t=...`: consume a short-lived, single-use token and establish a secure session.
- `POST /api/billing/checkout`: create or reuse an unexpired Razorpay subscription with the two-month future `start_at`; return only the public key, subscription ID, displayed trial end, and checkout configuration.
- `POST /api/billing/confirm`: validate the checkout signature and fetch provider state for immediate user feedback. It must not trust client-reported payment success.
- `POST /api/webhooks/razorpay`: verify the signature against the raw request body, deduplicate by Razorpay event ID, update state transactionally, enqueue notifications, and return promptly. Razorpay specifically requires raw-body signature validation and retry-safe webhook handling. [Webhook validation](https://razorpay.com/docs/webhooks/validate-test/), [webhook retry guidance](https://razorpay.com/docs/webhooks/faqs/).
- `POST /api/auth/magic-link` and `GET /auth/callback`: create a 15-minute one-use token, then set a revocable 30-day `Secure`, `HttpOnly`, `SameSite=Lax` session cookie.
- `GET /api/account`: return watchlist, access status, trial/renewal date, recent payments, and cancellation state.
- `PATCH /api/account/watchlist`: validate and atomically update tickers in PostgreSQL and Brevo.
- `POST /api/account/cancel`: require CSRF protection and confirmation; perform the appropriate provider cancellation and record access through the applicable period.
- `POST /api/account/restart`: create a new mandate without another trial and schedule it after any remaining access.
- `POST /api/unsubscribe`: stop future digest delivery and cancel renewal after explicit confirmation; do not mutate state on a GET because email security scanners follow links.
- `/digest?t=...`: replace ticker-bearing v1 tokens with short-lived v2 tokens containing customer ID, audience, expiry, and token version. Resolve the current watchlist and entitlement from PostgreSQL on every request.

### Lifecycle behavior

- `subscription.authenticated`: mark trial used, enable access through `trial_end`, add/upsert the customer in Brevo, and send welcome/trial-date confirmation.
- `subscription.activated` or `subscription.charged`: record the payment idempotently, set active access through the provider period end, clear grace state, and enqueue a receipt.
- `subscription.pending`: retain access for three days from the first failed renewal and send a payment-recovery notice.
- `subscription.halted`: stop access when grace expires and provide provider-supported payment recovery instructions.
- `subscription.cancelled`: retain only the locally promised trial/paid-period access; prevent further renewals.
- `subscription.completed`: stop further billing, alert the operator, and invite the customer to restart.
- Late or out-of-order events must never shorten already-paid access incorrectly. Compare provider timestamps, use unique payment/event IDs, and reconcile ambiguous state through the Razorpay API.
- Abandoned checkout records expire automatically. Repeated signup or checkout requests reuse an eligible open subscription instead of creating duplicate mandates.
- A late successful retry restores access. A charge received after an immediate cancellation is flagged for reconciliation and possible refund.
- Disputes/chargebacks flag the account for operator review and suspend access according to the support runbook.

## Website, Email, Operations, and Compliance

### Customer experience

- Replace every “free” claim with: “2 months free, then ₹100/month. Cancel anytime.”
- Add a clear pricing section, renewal date explanation, supported recurring methods, grace/cancellation/refund summaries, and FAQ coverage.
- Change signup to: email and tickers → email verification → trial terms summary → Razorpay mandate authorization → confirmed account.
- Require an unchecked consent box linking to Terms, Privacy Policy, and Cancellation/Refund Policy.
- Add a passwordless account page for watchlist editing, plan status, renewal date, payment history/receipts, cancellation, restart, and support.
- Add public Terms, Privacy, Cancellation/Refund, Contact/Grievance, and financial-news disclaimer pages. Include merchant legal name, address, contact details, response process, recurring-payment disclosure, data uses/processors, retention/deletion process, and “news—not investment advice” language.
- Have Indian counsel/CA confirm the final documents, GST registration/applicability, invoice fields, retention period, and merchant disclosures before production. The review should account for India’s [Consumer Protection E-Commerce Rules](https://consumeraffairs.nic.in/acts-and-rules/consumer-protection/consumer-protection) and current [DPDP notice expectations](https://www.meity.gov.in/writereaddata/files/Explanatory-Note-DPDP-Rules-2025.pdf).

### Email delivery

- Change the Railway digest cron to query eligible customers and watchlists from PostgreSQL, then send through Brevo’s transactional API.
- Add account-management and cancellation links to every digest. Continue mandatory billing/service notices even when normal digest delivery is suppressed where legally permitted.
- Send verification, welcome, trial-ending at seven days and one day, successful renewal, failed renewal, grace expiry, cancellation, restart, and refund messages.
- Keep Razorpay customer notifications enabled for mandate/payment regulatory events; ensure application emails supplement rather than contradict them.
- Configure and verify SPF, DKIM, DMARC, sender identity, support inbox, bounce handling, complaint suppression, and non-delivery monitoring.

### Existing subscriber migration

- Export and back up Brevo list 7 before cutover.
- Import normalized emails and tickers into PostgreSQL as verified legacy customers with `legacy_access_until = launch + 30 days` and unused trial eligibility.
- During the migration window, continue their existing email and digest access without payment.
- Send launch, 14-day, 7-day, and 1-day reminders. Authorization gives that customer a fresh two-calendar-month trial.
- At the deadline, stop digest delivery and web access for non-migrated users without creating any charge.
- Rotate the digest signing secret at cutover so old ticker-bearing links cannot bypass paid entitlement checks.
- Existing users entering the signup flow should receive a secure management/migration link rather than creating a duplicate account.

### Production operations

- Add separate test and live configuration for `DATABASE_URL`, Razorpay keys, plan ID, webhook secret, authentication/session secrets, Brevo settings, legal document versions, support address, legacy deadline, and `PAID_SERVICE_ENABLED`.
- Create a daily Railway maintenance job for provider reconciliation, expired grace/trial processing, migration reminders, email outbox delivery, abandoned-checkout cleanup, and anomaly reporting.
- Provide operator commands for import, customer lookup, reconciliation, access extension, refund, cancellation, magic-link resend, webhook replay, and export. Every mutation writes an audit entry.
- Add structured logs and alerts for webhook rejection/failure, database errors, reconciliation differences, duplicate subscriptions, email failures, payment failure rate, and unexpected entitlement changes.
- Track signup-to-mandate conversion, trial-to-paid conversion, active subscribers, MRR, churn, failed renewals, refunds, and migration conversion without exposing customer PII in analytics.
- Enable database backups/PITR and document restore testing, secret rotation, webhook-secret overlap during rotation, provider outage, database outage, charge dispute, refund, deletion request, and incident-response procedures.
- Never store payment credentials. Minimize stored webhook payload data, redact PII from logs, encrypt connections, rate-limit signup/auth/checkout routes, add bot protection after suspicious thresholds, and apply CSP and standard security headers.
- Use a feature flag for staged rollout. If billing creation must be disabled, preserve existing entitlements and mandates; do not silently cancel or double-charge customers.

## Test and Launch Plan

- Unit tests:
  - Calendar-month trial calculations, including leap years and month-end dates.
  - Trial eligibility, access derivation, cancellation, grace expiry, restart scheduling, and refund effects.
  - Email normalization, ticker validation, signed tokens, session expiry, CSRF, and idempotency.
  - Every Razorpay state transition, including duplicate, delayed, and out-of-order events.
- Integration tests:
  - PostgreSQL migrations and transactional constraints.
  - Razorpay test-mode checkout, signature verification, authentication, simulated first charge, retry, halted state, cancellation, refund, and webhook replay.
  - Brevo contact synchronization, lifecycle emails, bounces, and eligible-recipient filtering.
- End-to-end scenarios:
  - New subscriber completes verification and mandate, receives two free months, and converts on the correct date.
  - Checkout is abandoned, retried, closed after apparent failure, or authorized late.
  - Trial and paid cancellation, cancellation near renewal, restart with remaining access, and attempted second trial.
  - Failed renewal recovers inside grace or expires after three days.
  - Ticker changes affect the next email and existing digest links resolve the latest watchlist.
  - Existing subscriber migrates or misses the 30-day deadline.
  - Forged/replayed links, account enumeration, duplicate webhooks, provider outage, and database outage fail safely.
- Release gates:
  - Razorpay live account, Subscriptions, UPI AutoPay/cards/eMandate, plan, webhook, and settlement bank are verified.
  - Legal/tax review and customer-facing documents are approved.
  - Test-mode lifecycle passes with no duplicate charges or unauthorized access.
  - Brevo import totals and sample watchlists reconcile with PostgreSQL.
  - Staging runs through at least one complete simulated billing cycle.
  - Launch initially to operator/test accounts, then a small subscriber cohort, then all new signups, and finally the legacy migration campaign.
  - Monitor checkout, webhook, entitlement, send, and payment metrics closely for the first renewal cohort.

## Assumptions and Defaults

- India-only billing; US and Indian stock coverage remains available.
- Razorpay is the selected provider, subject to merchant approval and feature enablement.
- Trial is two calendar months, not 60 days.
- ₹100 is tax-inclusive and the maximum customer charge per month.
- Existing subscribers have a 30-day migration window and receive a fresh trial after mandate authorization.
- Cancellation is cycle-end with no prorated refund; failed renewal has a three-day service grace period.
- Passwordless email magic links are the only customer authentication method in v1.
- Managed PostgreSQL is authoritative; Brevo is retained only for delivery/contact synchronization.
