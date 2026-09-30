# Tickr Digest SEO quick-win audit

Audit date: 30 September 2026 (Asia/Singapore).

## Scope and confidence

Reviewed the homepage, company and AI overview templates, page handlers, client-side content loading, public utility/sample pages, and Vercel routing. The documented production URL is https://www.mydailydigest.online/. Web fetches could not reach it, and direct HTTP checks failed at DNS resolution in this environment. This is an unresolved live-verification limitation, not proof of a production outage. Findings below concern this repository; deployed behavior may differ.

No application code or deployment was changed. Search Console, rankings, traffic, live redirects, rendered Googlebot output and Core Web Vitals were not available or measured.

## Prioritized opportunities

| Priority | Finding and evidence | Recommended change | Indicative effort |
| --- | --- | --- | --- |
| 1 — High | Homepage links point to page anchors, home, or placeholder `#` links. Stock URLs are populated only after a visitor chooses a search result (`public/index.html`, `public/home-search.js:48–63`). | Add a visible “Explore Indian stocks” section with ordinary `<a href>` links to verified TCS, Reliance, Infosys and HDFC Bank company pages. Follow with a browsable stock directory. | 1–2 hours for starter links |
| 2 — High | No sitemap or robots.txt file or route is defined in this repository. Discovery currently depends on interactive search and links from personalized digests. | Publish `/sitemap.xml` containing home and verified public company URLs. Reference it from `/robots.txt` and submit it in Search Console. Include only canonical, successful pages; exclude utility, preview, private and invalid URLs. Missing robots.txt alone does not prevent indexing. | 2–4 hours for a small curated sitemap |
| 3 — High | Initial company HTML has an empty H1 and hidden, empty content containers (`templates/stock.html:24–32`; `templates/ai_overview.html:27–30`). JavaScript fetches the facts. `public/stock.js:543–562` builds only the selected tab, with AI Overview selected by default at line 582. | Render a cached company name, business description, sourced key facts, relevant links and freshness information in the initial response. Render core financial/news content without requiring clicks. Keep charts and interactive controls in JavaScript. Google can render JavaScript, but tab content requiring interaction is particularly vulnerable to being missed. | 1–3 days; highest-impact structural fix |
| 4 — Medium | Company descriptions are identical across symbols, titles initially use symbols, and both company templates omit canonicals and social metadata. Titles improve only after a successful API fetch. | Render company-specific titles and descriptions on the server, add an absolute self-canonical for each distinct useful page, and provide Open Graph tags. Example title: “TCS Share Price, Financials & News | Tickr Digest”. Example description: “Research Tata Consultancy Services (TCS): share price, reported financials, ownership and recent news. Explore sourced company data with Tickr Digest.” Keep AI pages self-canonical if their content is distinct. | 2–4 hours once company names are available server-side |
| 5 — Medium | Welcome, onboarding and several preview pages lack `noindex` in their HTML. The shared HTML response helper does not supply `X-Robots-Tag`. `design-preview.html` and `sample-digest.html` already have `noindex`. Legacy landing content already canonicalizes to home. | Apply `noindex` consistently to utility, preview and personalized digest pages through HTML or scoped response headers. Exclude them from the sitemap. Allow crawling so crawlers can see the directive; robots.txt blocking is not a substitute. Authentication remains responsible for privacy. | 1–2 hours |
| 6 — Medium | Public page handlers validate ticker syntax but do not establish company existence before returning 200 (`api/stock.py:17–29`, `api/ai_overview_page.py`). Invalid syntax returns 404; a well-formed nonexistent symbol can instead receive a loading shell and client error. | Resolve known nonexistent companies to a real 404 response. Handle temporary upstream failures separately, preserving cached valid company content where possible. Verify with one valid ticker, invalid syntax, a well-formed nonexistent ticker and a simulated provider failure. | Half a day |

Effort estimates are planning estimates, not measured implementation times. Impact reflects likely discovery/indexing benefit, not promised ranking or traffic gains.

## Existing strengths

The homepage already has a relevant title, description, absolute canonical, Open Graph tags, language declaration and mobile viewport. Company pages are public without sign-in. JavaScript updates company titles after loading. The stock data UI includes source/freshness information. Some sample pages already opt out of indexing.

## Suggested first pass

Ship priorities 1, 2, 4 and 5 together. Then render factual company content in the initial HTML and fix unknown-company status handling. Avoid treating social-image changes or generic schema additions as the main SEO project: discovery and accessible research content are the stronger opportunities here.

After deployment, inspect the homepage plus three company URLs in Search Console. Confirm that the rendered HTML includes company descriptions, facts and internal links; verify canonical selection and indexing eligibility. Check utility-page exclusion, sitemap processing and real 404 responses. Establish an impressions/clicks baseline and compare after 28 days, accounting for Google's crawl timing.

Verify the actual production hostname and its DNS before live checks. If the documented domain is outdated, update homepage canonical and social URLs to the preferred production origin and verify host redirects. Do not change the hostname based solely on this environment's failed fetches.

Performance needs a separate live measurement: no PageSpeed or Core Web Vitals score is inferred from the source.

## Supporting guidance

- Google: [Crawlable links](https://developers.google.com/search/docs/crawling-indexing/links-crawlable) — internal discovery should use real anchor URLs.
- Google: [JavaScript SEO](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics) — rendering, initial content, unique metadata and meaningful HTTP statuses.
- Google: [Build and submit a sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap) — include preferred canonical URLs and submit for discovery.
- Google: [Block indexing with noindex](https://developers.google.com/search/docs/crawling-indexing/block-indexing) — crawlers must be allowed to read the exclusion directive.

## Implementation follow-up — 30 September 2026

Priorities 1, 2, 4 and 5 are implemented in the working tree: four visible homepage
stock links; a curated five-URL sitemap and permissive robots.txt; server-rendered
company-specific metadata, canonicals and Open Graph tags; and consistent HTML
`noindex` directives on utility, preview and personalized digest pages. AI overview
pages link to their matching stock pages before JavaScript runs. Company names use
the existing bundled catalog with ticker fallback; no new provider calls are added.

Validation: all 171 Python tests and 17 relevant JavaScript tests pass. Additional
HTML/XML checks verified sitemap structure, homepage links, canonical page routes
and static utility-page exclusions. The sitemap companies are in the existing
catalog and their page handlers succeed locally; live provider coverage could not
be verified because the documented production hostname remains unreachable here.

These changes are local and have not been deployed or submitted to Search Console.
Initial factual content rendering and nonexistent-company status handling remain
follow-up work (priorities 3 and 6).

## Remaining fixes completed — 30 September 2026

Priorities 3 and 6 are now implemented. Stock and AI overview pages resolve the
company snapshot before responding and render a visible factual summary, name,
available prices, reported financial values with units/periods, news and related
company links in the initial HTML. Escaped JSON supplies the same snapshot to
browser code, avoiding its second core-data request. Charts and AI generation
remain interactive. Unresolved peer symbols are omitted safely.

Confirmed nonexistent companies return HTTP 404; temporary provider/access
failures return 503 rather than a successful loading shell. During transient
429/503 failures, an existing successful process-cache entry can be used for up
to one hour beyond its normal expiry. Its original retrieval time is retained
and the page explicitly warns about stale data. Missing companies and older
cached data are never served through this fallback.

Validation: 176 Python tests and 19 relevant JavaScript tests pass, including
safe markup/JSON output, zero and negative values, missing peer symbols,
404 versus 503, bounded stale fallback and bootstrap reuse. The local server was
restarted; real TCS stock/AI pages return 200 with server-rendered snapshots,
and a well-formed nonexistent company returns 404 on both page routes. The TCS
stock page was also inspected in the browser. Production remains undeployed.
