# Employer registry and source onboarding

## Scope and import

Implemented for the 25 October 2026 workbook. At the user's explicit request,
exclude `Ministries and departments`; counties are already absent. The imported
snapshot contains 796 directory rows, 758 employer records and 633 recruitment
URL strings after conservative normalization. These are not current vacancies,
unique legal-employer counts, or verified collection sources. Read the recorded
workbook SHA-256 in `config/employers.yaml` when comparing another workbook.

```sh
python -m ingest.employer_registry --workbook '/path/to/Kenya tech Jobs.xlsx' \
  --exclude-sheet 'Ministries and departments'
```

The importer reads XLSX values without executing formulas, macros or instructions.
It retains sheet/row provenance and caveats in the private configuration. Stable
import keys retain reviewed IDs, names, aliases and source verification on reruns.
Exact name plus official website host groups repeated records; it does not infer
that different names on the same board identify the same legal employer.
Removed rows are not automatically retired: review their existing records first.

- `config/employers.yaml`: employer identity, sector tags and workbook evidence.
- `config/employer-sources.yaml`: shared collection sources, platform suggestions,
  lifecycle, source-specific budgets and verification evidence. This extends the
  legacy `config/sources.yaml`; it does not replace the existing sources.
- `site/src/data/employers.json`: minimal public directory, generated from config;
  internal notes and verification records are not exported.

Review aliases and multiple URL variants before grouping a discovered underlying
board. Matching URLs deduplicate fetching, never employer identities. Multiple
active sources for the same platform/board/region are rejected.

## Verification and lifecycle

`pending → verified → trial → active`; separate `manual`, `blocked`, `retired`.
Runtime health is independent of this lifecycle. Import and discovery never
advance status or grant collection permission automatically. LinkedIn/Facebook
URLs start manual-only and are not fetched by this workflow.

An active or trial source requires a supported board and all of:
`official_link`, `collection_review`, `local_access`, `runner_access`, `stable_ids`,
`application_links`, `locations`, `dates_reviewed`, `complete`. Record evidence
paths plus a written `collection_basis`; do not mark these true on URL heuristics.
Check robots and relevant terms; a public API is not a redistribution licence.
Missing dates remain missing; update timestamps are not publication dates.

Each pilot source has a rank and official page to check. Incorrect URLs,
inaccessible pages, changed platforms, blocked requests and missing permission
remain visible rather than being promoted to meet a numerical target. Ashby's
robots route can return 401 even though its documented posting endpoint is
public. Only an explicit source-level reference to its public API documentation
permits one check of that endpoint; a block on the endpoint stops collection.

```sh
python -u -m ingest.employer_onboarding discover --output-dir /tmp/employer-local
```

Run **Verify employer recruitment sources** (`employer-discovery.yml`) with
`mode=discover` for GitHub-hosted access evidence. Results contain only sanitized
metadata and small title/ID/location samples; never descriptions or page bodies.
The 14-entry initial shortlist is a set of discovery candidates, not a claim
that 14 sources passed verification. See the recorded pilot report for outcomes.

## Isolated trial

```sh
python -u -m ingest.employer_onboarding trial \
  --source employer_SOURCE_ID --output-dir /tmp/new-employer-trial \
  --accepted /path/to/accepted/public/jobs.json
```

Choose the first 5–10 sources that pass all checks. The hosted workflow supports
the same trial and reads the accepted export for duplicate comparisons. A trial
requires a new/empty output directory and never runs the production finalizer,
writes canonical state, changes expiry counters/baselines, pushes data, or deploys.
It writes `candidate/*.json`, `audit.json` and `report.md`; missing verification
produces `NOT_VERIFIED`, not an implicit bypass. No supplied baseline means the
additional-unique-job metric is unknown. Trial exports include only CONFIRMED or
LIKELY technical jobs; other eligibility decisions remain in the audit.

Supported reusable connectors: Ashby, Greenhouse, Lever and public Breezy pages.
Malformed API shapes and missing structured vacancy records fail distinctly from
a valid empty board. Lever pagination and all network requests are bounded.
Prospect posts/talent pools, training enrolment and volunteer signups are excluded;
employment, internships, consultancies and fellowships are tagged separately from
the provider's employment terms. Descriptions supply scoped evidence in memory.

For multi-employer boards, do not assign every vacancy to the first listed
employer. Leave individual employer identity unresolved unless source fields or
reviewed board settings establish it. Sector is separate from job category.

## Production and scheduling

Production only loads `active` sources with complete recorded evidence. Manual
`--source` cannot bypass that gate. Absence expiry stays disabled for all new
registry sources, including new Ashby boards. Existing sources keep their policy.
Daily due checks apply even to manual production fetches and respect cooldowns;
failures back off exponentially to a maximum seven-day interval. Failed or partial
fetches retain previous accepted jobs. An initially empty, validated employer board
can be healthy; unexpected inventory drops still trigger the existing gates.

The current scheduler, updated on remote main before this implementation, has
five EAT slots: 06:00, 09:00, 12:00, 15:00 and 19:00. Employer-specific due checks
reuse those slots; the Worker schedule is not changed by onboarding.
The ingestion workflow also checks at most two due shortlisted discovery sources
per slot, at an independent eight-request budget each and a weekly interval.
Discovery does not scan all 633 portals. A recorded deliberate block stops future
automatic discovery checks until reviewed; manual rechecks require a reason.

Canonical occurrences remain separate; public exports merge exact duplicate IDs
or canonical application URLs while retaining attribution and the existing ID.
Direct-source metadata enriches exact matches and supplies the original employer
application link. Bare requisition numbers across employers are never matched;
fuzzy company/title similarity is not an automatic merge criterion.

## Website and delivery

`/employers/` is a static searchable directory with sector filtering and incremental
display. Careers links are explicitly distinguished from collected vacancies;
unverified links are labelled and directory records never enter job counts.
The home page adds direct-employer filtering; employer/sector controls appear only
when actual job metadata supplies them. Posting, closing and last-check times are
displayed separately when supplied. Directory links to collected jobs only appear
when the accepted export contains jobs assigned to that employer.

New registry jobs appear in All Jobs only, without creating employer panels or
changing existing panel order. No runtime backend/database or new recurring
scheduler is introduced. Read `docs/source-panels.md` for local/live acceptance.

Validate with Python tests/lint, frontend behavior tests, Astro check/build, then
browser-check accepted data and the deployed URL. Deploy using the existing
**Deploy TechKazi site** workflow. Roll back the code/frontend deployment without
rewriting job state or deleting scheduler claims. Retire sources explicitly and
preserve their historical attribution rather than deleting accepted jobs.
