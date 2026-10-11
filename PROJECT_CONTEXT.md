# TechKazi — Project Context (v0.1, Final)

Brand chosen on 11 October 2026: **TechKazi**. Current public address:
**https://techkazi.pages.dev/**. Future custom domain: **techkazi.com**.
The repository remains `kimtour/techjobs-africa`; existing job and scheduler
identifiers retain their original identity. See `docs/techkazi-branding.md`.

> This is the authoritative engineering context. If M0 discovery contradicts an assumption here, document the evidence and make the smallest necessary change. Do not redesign unrelated parts.

## 1. Product goal

Build a minimalist, high-density technology jobs aggregator for African candidates, modeled on TechURLs/DevURLs.

Core question:

> Which technology jobs can African professionals realistically apply for?

The product aggregates:
- local African tech jobs
- Africa-remote jobs
- worldwide-remote jobs
- relevant EMEA jobs
- employer ATS listings

The site is a discovery layer only. Every job links out to the original employer, ATS, recruiter, or job-board URL.

Differentiator: eligibility. "Remote" does not automatically mean "Africa remote". Every job carries an eligibility level plus evidence.

Constraints:
- About $0/month application infrastructure, excluding domain registration
- Solo-developer friendly
- Low-bandwidth/mobile-first
- Minimal JavaScript
- Store minimal parsed fields only
- Attribute sources
- Respect robots.txt and Terms of Service
- Never circumvent deliberate access restrictions

Non-goals for v0.1:
- accounts
- saved jobs
- alerts/digests
- employer dashboards/submissions
- payments
- CV upload
- application tracking
- per-job internal pages
- AI matching/classification
- runtime backend/API

## 2. Frozen stack

| Layer | Choice |
|---|---|
| Ingestion | Python 3.11+, httpx, selectolax, feedparser, Pydantic v2, RapidFuzz, PyYAML |
| Tests/lint | pytest, pytest-httpx or respx, ruff |
| State | JSON on a private `data` Git branch |
| Frontend | Astro static output + Tailwind CSS + TypeScript where needed |
| Search | Compact `search-index.json` + MiniSearch or simple normalized filtering |
| Scheduler | GitHub Actions, private repo, every 3 hours |
| Hosting | Cloudflare Pages, Direct Upload via Wrangler |
| Alerts | Telegram Bot API, plain text |
| Analytics | Cloudflare Web Analytics |

Explicitly absent in v0.1:
- database
- runtime backend/API
- Redis
- FastAPI
- Celery
- Airflow
- Elasticsearch
- Vercel ISR
- Kubernetes
- GraphQL

Playwright is last resort only if M0 proves it unavoidable and the reason is documented in `config/sources.yaml`.

Pin dependencies before production CI. Use currently documented major versions of GitHub Actions and Cloudflare Wrangler tooling at implementation time.

## 3. Exact initial sources

Never substitute these URLs during M0.

| id | URL | Current status |
|---|---|---|
| `myjobmag` | https://www.myjobmag.co.ke/jobs-by-field/information-technology | Method unverified until M0 |
| `corporate_staffing` | https://www.corporatestaffing.co.ke/category/it-jobs-in-kenya/ | Method unverified until M0 |
| `openedcareer` | https://openedcareer.com/job-category/computer-science/ | Method unverified until M0 |
| `elevolt` | https://jobs.elevolt.co.ke/jobs/category/software-it?page=1&location=&type=&qualification=&search= | Method unverified until M0 |
| `greenhouse` | https://my.greenhouse.io/jobs/search?location=Kenya&lat=0.554064&lon=37.903148&location_type=country&country_short_name=KE&work_type[]=remote | Discovery aid only; production ingestion should use company Job Board API tokens discovered later |
| `ashby` | https://jobs.ashbyhq.com/talentsafari | Use official posting API only if M0 confirms it |

Method priority:
1. official documented API
2. RSS / Atom
3. public/documented JSON
4. server-rendered HTML
5. embedded/internal JSON
6. browser automation as last resort

## 4. M0 discovery is mandatory

Do not implement production source adapters before M0 is complete.

Run discovery:
1. locally
2. from a GitHub Actions hosted runner

For each exact source record:
- requested URL
- final URL
- HTTP status
- redirects
- content type
- response size
- robots.txt status
- whether target path appears allowed for the configured user agent
- Terms/automation notes
- API/RSS/JSON/HTML availability
- JS dependency
- pagination clues
- crawl completeness
- visible job count if safely detectable
- available fields
- date/deadline clues
- original apply URL availability
- GitHub runner accessibility

Deliverables:
- `docs/source-discovery.md`
- `m0-results.json` artifact
- filled `config/sources.yaml`
- minimal sanitized fixtures under `tests/fixtures/`

Do not invent results.

If a source blocks automation:
1. determine whether the block is incidental
2. look for an official API/feed
3. contact the source owner if appropriate
4. otherwise disable/drop the source

Never implement proxy/evasion logic to bypass a deliberate block.

## 5. Repository layout

```text
techjobs-africa/                       # main branch
├── PROJECT_CONTEXT.md
├── README.md
├── .gitignore
├── .env.example
├── docs/source-discovery.md
├── site/{src/{pages,components,layouts,lib},public,astro.config.mjs,package.json}
├── ingest/
│   ├── adapters/{base,ashby,greenhouse,myjobmag,corporate_staffing,openedcareer,elevolt}.py
│   ├── normalize/
│   ├── classify/
│   ├── dedupe/
│   ├── expiry/
│   ├── health/
│   ├── export/
│   ├── models.py
│   ├── main.py
│   ├── finalize.py
│   └── m0_probe.py
├── config/{sources,ats_boards,geography,categories,agencies,quality_gates}.yaml
├── tests/{fixtures,adapters,normalization,classification,eligibility,dedupe,expiry}/
└── .github/workflows/{m0-discovery,ingest-and-deploy,link-health}.yml
```

Private `data` branch:

```text
schema_version.json
canonical/jobs.json
sources/<source_id>.json
state/{occurrences,health,duplicate-review,last-run,last-known-good,deployment}.json
public/{jobs,search-index,categories,countries,stats}.json
snapshots/last_known_good/
```

Every persisted file carries `schema_version`.

## 6. Data models

### Stable identity

Never derive permanent job IDs from mutable fields such as title, city, category, or a description hash.

Identity order:
1. ATS provider + external ID
2. persisted identity tied to canonical apply URL
3. persisted generated UUID

A title edit must not create a new unrelated job.

### JobOccurrence

Recommended fields:
- occurrence_id
- job_id
- source_id
- external_id
- raw_title
- raw_company
- raw_location
- source_url
- apply_url_original
- apply_url_canonical
- published_at
- published_at_source
- date_quality
- deadline_at
- first_seen_at
- last_seen_at
- missed_crawls
- active
- closure_reason
- link_status
- consecutive_dead_checks
- description_hash (agency matching only; never persist full description)
- salary (optional; define only if M0 shows useful coverage)

### CanonicalJob

Recommended fields:
- job_id
- title
- normalized_title
- posting_company
- hiring_company
- normalized_company
- is_agency_posting
- employer_identity_quality
- city
- country
- country_code
- country_source
- workplace_type
- geographic_scope
- eligibility_level
- eligibility_evidence
- eligibility_source
- timezone_requirement
- category
- secondary_categories
- category_source
- skills
- employment_type
- experience_level
- published_at
- date_quality
- published_at_source
- deadline_at
- status
- preferred_apply_url
- sources
- data_quality
- first_seen_at
- last_seen_at

Eligibility levels:
- CONFIRMED
- LIKELY
- VERIFY
- RESTRICTED
- UNKNOWN

Job statuses:
- ACTIVE
- STALE
- CLOSED
- EXPIRED

Also define:
- `SourceHealth`
- `IngestionRun`
- `FetchResult`
- `RawJob`

## 7. Pipeline

```text
FETCH
→ EXTRACT
→ VALIDATE RAW
→ NORMALIZE
→ TECH-ONLY CLASSIFY
→ ELIGIBILITY CLASSIFY
→ DEDUPE / MATCH
→ EXPIRY
→ build CANDIDATE state in system temp directory
→ validate
→ build CANDIDATE public output
→ display hash
→ quality gates
```

If public content changed and gates pass:
1. build Astro
2. deploy Cloudflare
3. finalize candidate state
4. record deployment metadata
5. commit state to `data`

If public content is unchanged:
1. finalize operational state
2. commit legitimate state changes
3. skip build/deploy

If gates fail:
- do not deploy
- alert
- commit only safe operational/health metadata
- keep last-known-good site live

Each source is isolated. One failing source must never modify another source's records.

Jobs present in a crawl must refresh `last_seen_at` even when absence processing is disabled.

Bootstrap auto-detects empty/uninitialized state:
- no new-job alert flood
- no expiry
- no absence processing
- clean first_seen initialization

## 8. Eligibility rules

Positive eligibility signals may come from:
- structured ATS fields
- title
- location string
- a small applicant-directed description whitelist

Descriptions are processed in memory only and never persisted.

Rules:

| Condition | Result |
|---|---|
| Structured field/location/title names an African country/city | CONFIRMED |
| Structured location explicitly worldwide | CONFIRMED |
| Description-only applicant-directed Africa phrase | LIKELY |
| EMEA or regional scope with unclear country coverage | VERIFY |
| Bare Remote | UNKNOWN |
| Legal/residency phrase paired with non-African location | RESTRICTED |

Required non-rules:
- "clients in Ghana" is not an eligibility signal
- "customers worldwide" is not an eligibility signal
- "must reside in Kenya" is not restricted
- "authorized to work in Nigeria" is not restricted
- timezone overlap never means restricted
- "join us"/"contact us" must never match country code US
- bare EMEA/worldwide/work-from-anywhere in generic description text is not enough
- applicant-directed worldwide phrase in description may be LIKELY; structured worldwide may be CONFIRMED

EMEA never automatically confirms Kenya eligibility.

## 9. Tech-only classification

Use `config/categories.yaml`.

Primary taxonomy:
- Software Engineering
- AI / Machine Learning
- Data Engineering
- Data Science
- DevOps / SRE
- Cloud
- Cybersecurity
- Application Support
- Systems Administration
- Networking
- QA / Testing
- Database
- ERP / Enterprise Systems
- Solutions Architecture
- Technical Support
- UI / UX
- Technical Product
- Technology Leadership
- Internship / Graduate Technology

Use reliable source categories first, then deterministic title/keyword rules.

Treat generic "Product Manager" as Technical Product, per the explicit product decision recorded
in `config/categories.yaml`.

Experience filter is conditional on M0 data quality.

## 10. Geography

`config/geography.yaml` must cover all African countries and relevant cities before eligibility logic depends on it.

Never make `Worldwide` an alias for Africa.

Keep separate concepts for:
- Africa
- Sub-Saharan Africa
- EMEA
- Worldwide
- United Kingdom
- European Union
- United States
- Canada
- other non-African regions used in restriction rules

Avoid matching 2-letter country codes freely in prose.

## 11. Deduplication

Order:
1. ATS provider + external ID
2. canonical apply URL
3. normalized company + title + city + country when employer identity is reliable
4. agency/confidential: skip normal company fingerprint; optionally use same agency + normalized title + city + description hash
5. RapidFuzz similarity -> review flag only, never auto-merge

Keep all occurrences.

Preferred apply URL should favor the employer's own application URL when available.

## 12. URL rules

Keep:
- apply_url_original
- apply_url_canonical

Strip only known tracking parameters such as:
- utm_*
- fbclid
- gclid

Preserve functional parameters and unknown parameters by default.

Allow only http/https outbound URLs.

Reject javascript/data/file/malformed URLs.

## 13. Dates

Keep separate:
- source_published_at
- source_updated_at
- deadline_at
- first_seen_at
- last_seen_at

Relative dates use the configured source timezone.

Unknown timezone => mark approximate.

Missing publish date => `published_at = null`, `date_quality = FIRST_SEEN_ONLY`.

## 14. Source health and pagination

Every source run records:
- status
- records_found
- pages_fetched
- crawl_complete
- last_attempt_at
- last_success_at
- safe_to_process_absences

Statuses:
- SUCCESS
- PARTIAL
- FAILED
- BLOCKED
- DISABLED

A job falling off page 1 does not mean closed.

Absence processing requires all:
- healthy crawl
- sufficient/complete pagination
- source supports absence-based expiry
- not bootstrap

Use source-specific historical counts. Example:
- current count < 50% of trailing median
- mark suspicious
- disable absence processing

## 15. Expiry and link health

Expiry precedence:
1. source says closed
2. two consecutive confirmed 404/410 checks
3. deadline passed
4. absent from 3 successful complete crawls
5. source-specific TTL

A single 404 never expires a job.

Weekly link-health workflow:
- 200/valid redirect -> LIVE
- 404/410 confirmed twice -> DEAD
- 403 -> BLOCKED
- 429 -> RATE_LIMITED
- 5xx/timeout -> UNKNOWN

403/429/5xx/timeouts never close a job.

## 16. Crawl budgets

Each source supports:
- enabled kill switch
- max_pages
- max_requests_per_run
- request_delay_ms
- timeout_seconds
- retry_delays_seconds
- Retry-After handling

Do not aggressively retry.

## 17. Git state / CI ordering

Use:
- `main` for code
- `data` for persistent state

All state-writing workflows share one concurrency group.

Use:
```yaml
concurrency:
  group: techjobs-pipeline
  cancel-in-progress: false
```

Set timeout-minutes.

Use GitHub step outputs, not tracked marker files.

Candidate staging must be outside the tracked data directory.

Push flow:
- fetch
- fast-forward-only
- retry once after reloading on rejection
- no automatic rebase for JSON state

No automatic force-squash workflow in v0.1.

## 18. Display hash and quality gates

Display hash includes only display-affecting fields:
- job ID
- title
- company
- location
- workplace type
- category
- skills
- eligibility
- apply URL
- status

Do not hash timestamps/health/runtime metadata.

Use configurable quality gates from `config/quality_gates.yaml`.

Maintain:
- last_successful_public_hash
- last_successful_deployment_id
- last_known_good snapshot

Suspicious candidate data must not deploy.

## 19. Frontend

Desktop default:
- Sources view

Mobile default:
- All Jobs feed

Provide:
- Sources | All Jobs toggle
- dense rows
- source attribution
- time filters
- country
- workplace type
- category
- eligibility
- posted date

Experience only if M0 data is good enough.

Use `localStorage` for:
- hidden sources
- source order
- default view
- theme
- filter preferences

No accounts.

No per-job pages in v0.1.

Static pages may include:
- `/jobs/`
- `/jobs/<category>/`
- country pages
- `/remote/`
- `/remote/africa/`
- `/remote/worldwide/`
- `/about`
- `/feed.json`
- `/rss.xml`

Search:
- compact `search-index.json`
- MiniSearch or simple normalized filtering
- no Pagefind in v0.1

## 20. Alerts and security

Telegram plain-text alerts for:
- adapter exception
- zero-item crawl
- >50% count drop
- 403/429
- persistent 5xx
- deploy failure
- state validation failure
- quality-gate failure

Never spam bootstrap.

Secrets only in GitHub Secrets:
- CLOUDFLARE_API_TOKEN
- CLOUDFLARE_ACCOUNT_ID
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

Use least privilege.

Treat all scraped text as untrusted:
- strip unnecessary HTML
- escape rendered text
- normalize Unicode
- limit field lengths
- validate URLs
- never execute scraped content

Do not store descriptions or recruiter personal contact data.

## 21. Development order

### M0
Discovery:
- exact six URLs tested locally and on GitHub Actions
- source matrix
- robots/ToS notes
- minimal fixtures
- repo + data branch initialized

### M1
Vertical slice:
- models
- bootstrap
- Ashby adapter
- Greenhouse adapter
- canonicalization
- simple Astro page
- Cloudflare deploy

### M2
Local sources:
- MyJobMag
- Corporate Staffing
- OpenedCareer
- Elevolt

### M3
Processing:
- tech-only classification
- location normalization
- eligibility
- dedupe
- expiry
- health

### M4
Frontend:
- Sources
- All Jobs
- filters
- search
- mobile
- dark mode
- hide/reorder
- SEO pages

### M5
Hardening:
- fixture tests
- failure-mode tests
- pagination tests
- dedupe/agency tests
- alerts
- weekly link health
- rollback
- analytics

### M6
Launch

## 22. Required tests

Eligibility:
- Remote -> UNKNOWN
- Remote - EMEA -> VERIFY
- Remote - Kenya -> CONFIRMED
- Must reside in Kenya -> not RESTRICTED
- Must reside in United States -> RESTRICTED
- 4 hours overlap with EST -> not RESTRICTED
- west timezone -> not RESTRICTED
- join us / contact us -> no US-country match
- clients in Ghana -> no eligibility inference
- Worldwide customer base -> no eligibility inference
- Open to candidates in Africa, description only -> LIKELY
- structured worldwide -> CONFIRMED
- African city/location matches -> CONFIRMED

Identity/dedupe:
- same ATS ID
- same apply URL
- title correction preserves ID
- senior vs non-senior not merged
- agency confidential jobs not incorrectly merged
- same job on two sources displayed once

Expiry/health:
- failed crawl leaves absence counters untouched
- partial crawl
- 403
- 429
- soft 404
- two 404s
- deadline expiry
- page1-only roll-off
- first-run bootstrap
- present jobs refresh last_seen even if absence processing is gated

State/site:
- schema_version
- deterministic sorted output
- corrupt staging aborts
- display hash ignores timestamps
- unsafe URLs rejected
- no unescaped scraped HTML

## 23. Do not

Do not:
- add infrastructure because it might be useful later
- add a database prematurely
- store full descriptions
- put mutable fields/description hashes into permanent job IDs
- circumvent explicit anti-bot restrictions
- auto-merge fuzzy duplicates
- treat EMEA as automatically Kenya-eligible
- treat timezone overlap as residency restriction
- treat 403/429/5xx as dead
- treat page-1 absence as closed
- deploy suspicious mass-deletion datasets
- use tracked marker files
- stage candidate state inside tracked data
- prefer AI classification over deterministic rules in v0.1

## 24. First tasks for the coding agent

Do these in order:

1. Read this file completely.
2. Scaffold the repo layout with pinned deps, ruff/pytest config, and empty modules.
3. Create the data-branch bootstrap script and state schemas.
4. Use the exact six URLs in `config/sources.yaml`.
5. Create/configure `geography.yaml`, `categories.yaml`, `agencies.yaml`, `ats_boards.yaml`, `quality_gates.yaml`.
6. Run the local M0 probe.
7. Run `.github/workflows/m0-discovery.yml`.
8. Record real findings in `docs/source-discovery.md`.
9. Save only minimal sanitized fixtures.
10. Stop and review M0 results before production adapters.
11. Then implement models and eligibility tests.
12. Then implement the Ashby + Greenhouse vertical slice.

If discovery contradicts an assumption, document the evidence and make the smallest necessary change.
