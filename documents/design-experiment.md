# Legacy / modern design flag

Both presentations are retained. `legacy` is the design from pre-session Git commit
`e2d9ac6` (the full revision is recorded in `templates/legacy/README.md`);
`modern` is this session's navy-and-mint redesign. No randomized experiment is active.

## What is implemented

- `DIGEST_DESIGN=modern` is the default for rendered email and web digests.
- `DIGEST_DESIGN=legacy` selects the old HTML templates and old plain-text email presentation.
- Set the flag on **both** Railway (email jobs) and Vercel (web/API); restart/redeploy those services after changing configuration.
- A valid `?design=legacy` or `?design=modern` on an authenticated `/digest?t=…` link overrides the deployment default. The existing signed token is still required; the flag grants no data access.
- Email rendering adds its variant to the full-digest link. Progressive ticker requests also carry the shell's variant, so email, shell, and fragments stay consistent even if the default later changes.
- Renderers accept an explicit `design="legacy"` or `design="modern"` argument for a future assignment service. Unknown request values fall back to the deployment default; an invalid environment flag raises a configuration error.
- Old and new presentation templates have separate Jinja loaders. Earnings and price partials are preserved with the legacy templates. Collection, AI generation, signing, and delivery are shared.

The landing page is static: the Python environment flag does **not** select it.
`/?design=legacy` redirects to `/legacy/index.html`; `/?design=modern` opens the new
landing page. This is a preview switch, not an experiment assignment or a persistent cookie.
A JavaScript-free legacy URL is `/legacy/index.html`.

## Local comparison

Open `/design-preview.html` for links to all six previews.

| Surface | Legacy | Modern |
| --- | --- | --- |
| Landing | `/legacy/index.html` | `/` |
| Email preview | `/legacy/preview-email-digest.html` | `/preview-email-digest.html` |
| Full digest sample | `/legacy/sample-digest.html` | `/sample-digest.html` |

Regenerate preview fixtures for either variant:

```sh
DIGEST_DESIGN=legacy .venv/bin/python scripts/preview_digest.py
DIGEST_DESIGN=legacy .venv/bin/python scripts/preview_email_digest.py
DIGEST_DESIGN=legacy .venv/bin/python scripts/build_landing_sample.py
```

Use `DIGEST_DESIGN=modern` for modern output. Each writes to its own public directory;
neither overwrites the other variant. These commands use fixture data and do not send emails.

## Recommended experiment rollout (not implemented yet)

1. Start with one subscriber experiment, separate from landing-page acquisition.
   Assign a stable Brevo contact ID to a variant using a deterministic hash of
   `experiment_id + contact_id`, or store the assignment in a contact attribute.
   Start at a small modern allocation, then expand to 50/50 after checking errors.
   Never choose a fresh random variant on each send or page load.
2. Pass that assignment to `build_email_digest(..., design=variant)`.
   Its generated link carries the same design to the web page. Persist the experiment
   ID and assignment so changes to traffic allocation do not reshuffle existing users.
3. Track experiment ID, assigned variant, and actual displayed variant on email sends,
   unique full-digest clicks, successful digest loads, and unsubscribes.
   Use unique digest clicks per delivered email as a primary engagement measure;
   monitor loading errors and unsubscribes as guardrails. Email opens alone are a
   weak measure because client privacy features can distort them.
4. Run landing-page acquisition as a separate experiment using a first-party visitor
   assignment at the server/edge, retained in a cookie. Measure confirmed subscriptions
   per assigned visitor. Decide explicitly whether to transfer that assignment after signup.
5. Keep content, audience, and sending times consistent between variants. Note that
   the current designs also differ in information placement: legacy email includes
   prices, modern email focuses on AI + news. This experiment compares the complete
   experience, not typography alone.
6. Add a kill switch that overrides both saved assignments and URL overrides before
   enabling a real experiment. The current environment flag is a **default**, not a
   kill switch: already-sent variant links intentionally keep their design.

Declare the metric, minimum sample, and evaluation period before launch. Keep both
implementations through the experiment and rollback period, then remove the losing
presentation in a separate, deliberate change.

## Targeted enablement

`config/design_overrides.json` maps normalized recipient email addresses to a design.
The sender resolves this before rendering and pins the same variant on the digest URL.
The configured recipient `paras.dhawan17@gmail.com` uses `modern` even when the global
flag is `legacy`. Unlisted recipients retain the deployment default. This is a targeted
rollout, not a randomized experiment. Deploy the updated sender and web code before
expecting production emails to use this behavior; previously delivered emails do not change.
