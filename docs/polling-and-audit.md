# Polling and fetch audit

## Assessment and observed failures

The previous setup was serviceable for a first version, but not sufficiently
observable or resilient for unattended polling. The audit on 1 October 2026 found:

- [30 September run 36698064920](https://github.com/kimtour/techjobs-africa/actions/runs/36698064920)
  completed fetching but failed to push the data branch because another run had
  advanced it. Scheduled and manual runs had no shared concurrency lock.
- [29 September run 36588741960](https://github.com/kimtour/techjobs-africa/actions/runs/36588741960)
  failed before fetching because `requests` was missing from dependencies. The
  dependency has since been pinned in `requirements-dev.txt`.
- Four recent runs were cancelled during their ingestion step. Cancellation is
  an incomplete attempt, not evidence of a source outage.
- GitHub scheduled executions were irregular. Cron is a requested schedule,
  not a guarantee of start time or completion time.
- The old runner declared every returned list a complete, successful one-page
  crawl. Fuzu caught a timeout and returned the fetched prefix, so an incomplete
  crawl could appear successful. Page caps could also go unreported.
- Source errors were swallowed without error categories, and rebuilding the
  dataset from only successful sources could remove a failed source's listings.
- The configured retry delays and request budgets were not applied consistently.
- Source health had no attempt/success times. `state/last-run.json` was unused.
  Historical workflow records cannot establish individual source fetch times.

These are separate from the location extraction issue. Fetch freshness alone does
not establish that location parsing or listing coverage is correct.

## Current schedule

Cloudflare is the active scheduler. Its deployment evidence, live status page,
and rollback checks are documented in
[Cloudflare fetch scheduler](cloudflare-scheduler.md). GitHub's native cron is
disabled to avoid requesting duplicate fetches.

Use five runs per day, every day, in Africa/Nairobi (EAT, UTC+3):

| Morning | Midday | Afternoon | Evening |
|---|---|---|---|
| 06:00, 09:00 | 12:00 | 15:00 | 19:00 |

The overnight gap is eleven hours (19:00–06:00). The daytime gaps are three
hours, with four hours between 15:00 and 19:00. This replaces the nine-slot
schedule to reduce Actions minute consumption. At the user's request, all
triggers are scheduled at the top of the hour.
This is an evidence-informed starting policy, not a measured optimum. There is
not yet a reliable source-specific arrival-rate history to justify hourly full
crawls. No separate Codex automation is needed: the Cloudflare Worker requests
fetches, and `.github/workflows/ingest-and-build.yml` executes the ingestion and
publication pipeline.

GitHub can queue externally dispatched work, and its concurrency queue can replace
an older pending run with a newer pending run. Running work is not automatically
cancelled. Read actual attempt times, not cron, when assessing freshness. If
precise on-time fetching becomes a hard requirement, run ingestion in a direct
execution environment rather than relying on GitHub runner availability.

## Safe request and publication policy

- All state-writing workflows share `techjobs-pipeline`; never force-push JSON
  state or automatically rebase snapshots. An external writer must use the same
  group. A rejected push fails visibly and the audit artifact remains available.
- Each run is capped at 25 minutes. Each source has finite page/request budgets,
  configured timeouts, and at least the configured gap between requests.
- At most two retries for transport failures, HTTP 429, and selected transient
  5xx responses. Delays are 5 and 20 seconds plus small jitter. Honor Retry-After
  as seconds or an HTTP date. A delay over 120 seconds defers the source until
  its recorded next-allowed time. HTTP 401/403 and other permanent 4xx responses
  are never retried. Do not change identity or evade deliberate source blocks.
- HTTP counts reflect actual attempts. Page counts reflect successful page
  responses; completeness comes from the adapter's terminal pagination signal.
  MyJobMag completeness refers to its approved 30-day lookback, not all history.
- Failed, blocked, empty, or suspicious source responses retain that source's
  previous accepted records. A bounded partial crawl can refresh observed jobs
  while preserving unseen records. Large source drops use the configured 60%
  threshold against a trailing seven-success median and prior technical count.
- Total active-job drops over 50% block publication. A first-run empty result is
  treated as suspicious; legitimate emptiness needs investigation before relaxing
  the gate. Raw count success does not prove a source parser is correct.
- Missing means unobserved, not closed. Only Ashby's complete official API is
  currently configured to support absence expiry: three successful complete
  misses, with no absence processing on bootstrap. Other sources retain unseen
  jobs until a separately supported closure/expiry policy is established. This
  trades some stale listings for protection against disappearing jobs.
- Use an isolated candidate. Build and deploy only when public JSON changes.
  Promote canonical data, occurrence state, and baselines only after successful
  deployment, or immediately if public content is unchanged. Build/deploy failures
  keep the previous public snapshot; operational audit state still commits.
- Emit a warning on each source problem. After two consecutive bad source runs,
  fail the final workflow attention step, even if healthy-source updates were
  safely published. GitHub notification delivery depends on the user's repository
  subscription settings; no email/Telegram sender is configured by this change.

## What is logged and where to find it

Every completed run appends a JSON record under
`data:state/fetch-history/YYYY-MM-DD.jsonl`. Logs use UTC timestamps; the GitHub
summary and report command display EAT. The record includes:

- Run ID and attempt, workflow evidence URL, start/end, overall outcome,
  publication eligibility, content hash/change flag, and attention flag.
- Per-source start/end/duration, last attempt and last successful complete fetch,
  hours since success, consecutive problems, status, stop reason/error class.
- Actual requests, retries, successful pages, HTTP status histogram, raw and
  technical counts, new/updated/missing counts, retained count, and request events.
- Completeness and absence-safety decisions, and Retry-After cooldown.

Request events are also flushed immediately to
`state/request-history/YYYY-MM-DD.jsonl`; `state/fetch-progress.json` identifies
an interrupted source even when the final run summary was never written.
`state/health.json` and `state/last-run.json` provide the latest snapshots.
`state/publication-history/YYYY-MM-DD.jsonl` separately records deployment outcome,
URL/ID when available, and whether candidate state was promoted. Workflow status
in that record is status at finalization, not the later terminal Actions result.

A readable **Fetch audit** table appears in each GitHub Actions run summary.
A `fetch-audit-RUN_ID-ATTEMPT` artifact is uploaded on success or failure and retained
for 90 days. Daily logs remain on the data branch, backed by its Git history.
If a job is hard-killed or fails before ingestion, artifact upload is not
 guaranteed; use the Actions step log. No source fetch should be inferred for a
run that never reached ingestion.

Logs contain metrics, error classes, and endpoint hostnames. They never include
response bodies, descriptions, contacts, credentials, exception messages, or
request query strings. They are operational records, not a public-site export.

Read saved logs without fetching any source:

```bash
python -m ingest.audit_report --data-dir /path/to/data-checkout --last 20
python -m ingest.audit_report --data-dir /path/to/data-checkout --source fuzu --last 20
```

## Review after two weeks

Compare source-specific job arrivals, unchanged-run proportion, request volumes,
fetch duration, rate limits/timeouts, completeness, and gaps since last success.
A source with frequent new jobs and low request cost may warrant hourly daytime
polling. A low-change or rate-limited source may warrant a longer interval. Do
not increase frequency to compensate for a broken parser or incomplete crawl.

Investigate repeated count drops, empty results, missing publication dates, or
location quality by comparing allowed source metadata with the exported records.
The existing behavior tests cover basic parsing; they cannot detect every future
site markup change. Incremental fetching/conditional HTTP caching should only be
added for endpoints whose ordering, pagination, and cache-validator behavior have
been verified. A periodic complete reconciliation remains necessary.
