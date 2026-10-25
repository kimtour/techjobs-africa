# Daily employer vacancy collection

## Decision

Publish individual vacancies only. The 758-employer registry is a collection
inventory, not a website directory. Shared recruitment portals are fetched once
and mapped to their separate employers. There are 633 imported source URLs;
redirects, embedded boards and duplicate board URLs can reduce the fetch count
further, but require review before merging collection sources.

Keep the existing public code repository, private accepted-data repository and
single serialized publication pipeline. Both ingestion and publishing now run on
public standard hosted runners successfully. A second crawler repository plus a
private importer would duplicate coordination and reintroduce private-minute
limits on publication. No extra Worker change-detection layer is needed.

Preserve all five existing daily EAT slots. Spread approved employer sources
across them using per-source due times; measure runtime and requests before
changing schedules or increasing concurrency. Discovery/probing is separate from
vacancy collection and must not activate sources automatically.

## First milestone: full-list probe

```sh
python -m ingest.employer_probe --output-dir /tmp/employer-probe --workers 8
```

The manual **Verify employer recruitment sources** workflow also has mode `probe`.
It assesses the full registry, emits one metadata file per source, and generates
`coverage.json` with a row for every employer plus a human-readable `report.md`.
An interrupted local probe can resume with `--resume` in the same output folder;
reuse is limited to matching input URL and source lifecycle. Start a new folder
for a fresh assessment. A resumed report's request/runtime totals describe that
invocation, not the combined historical work.

The probe uses plain public HTTP, eight workers by default (maximum twelve),
shared per-host throttling of at least one second, robots checks and published
Crawl-delay, a maximum of twelve requests per source, bounded redirects, ten-second
request timeouts and a two-megabyte response limit. It follows at most one observed
same-host careers link. PDF URLs are detected without extracting their content.
Blocked hosts are not retried during the run; saved blocks also carry into a
resumed assessment. A Crawl-delay above sixty seconds is left for manual review. Social, manual and blocked sources
are skipped. Redirect destinations receive their own robots checks. Local/private
network destinations are rejected. Bodies are never persisted.

Methods are suggestions: ATS API, structured data, feed, PDF, link comparison or
needs review. A generic script-heavy page is not proof that a browser is required.
A detected API is not collection permission, and a reachable page is not complete
job coverage. The report separately counts employers with verified active
collection. Discovery does not produce "no new jobs" outcomes.

## Daily collector milestones

1. Review the full-list probe, official employer-to-board links, collection basis,
   pagination, regions and employment types. Resolve shared boards conservatively.
2. Expand reusable ATS collectors first, then structured JobPosting/feed sources.
   Add selected custom listing parsers and multi-role PDF extraction next.
   Browser automation requires a separately justified and permitted source.
3. Persist stable vacancy identity and compact metadata, alongside separate seen,
   awaiting-extraction, validated and published states. Retry failed extraction;
   discovering a link alone must not remove it from the pending queue. Never build
   identity from a mutable title. PDF roles require a requisition identifier or
   reviewed durable role mapping; a shared PDF/apply URL alone is not identity.
4. Fetch every required listing/pagination endpoint. Only reuse ETag,
   Last-Modified or hashes after checking the source's behaviour. An unchanged
   careers homepage or first page cannot skip other pages or embedded APIs.
   Fetch details for new/changed or pending jobs; classify while descriptions are
   in memory and persist only compact metadata and classification evidence labels.
5. Establish an initial source baseline in publication-disabled mode. Existing
   jobs may later be published as reviewed current vacancies, but must never be
   labelled newly posted. Show employer posting date separately from TechKazi's
   first-found date and last-checked time. Do not synthesize a posting date.
6. Apply existing technical and eligibility rules, then exact dedupe with employer
   application preference and preserved attribution. EMEA does not prove Kenya
   eligibility. Multi-role PDF adverts may share a destination; distinct durable
   requisition identities must remain distinct. No descriptions are retained.
7. Produce isolated candidate exports and daily coverage outcomes. Review before
   enabling publication, maintaining the existing source verification, trial and
   publication gates. New-source absence expiry stays off; failures cannot close
   jobs. Build/deploy only when the public output changed.

## Daily coverage contract

Each employer must have a dated result linked to its collection source and latest
successful complete crawl: new vacancies, no new vacancies, partial, failed,
blocked, unsupported/manual, not due under backoff, or candidates awaiting
validation. Distinguish source checks from employers covered and vacancies seen
from vacancies accepted/published. Do not count a skipped/backed-off/unsupported
employer as successfully checked that day. Measure actual configured coverage
and successful daily coverage separately. A successful workflow is insufficient.

The implemented collector framework supports reviewed Ashby, Greenhouse, Lever,
Breezy, JSON-LD, RSS/Atom, custom field mappings and multi-role PDFs. Five sources
have completed isolated local and hosted trials and are approved for daily
collection: M-KOPA, Jumia, Turaco, Ampersand and Tala. Other sources remain gated.
This is not complete vacancy collection across all 758 employers.
See [pilot results](employer-pilot-results.md) and
[onboarding gates](employer-onboarding.md).


## Implemented daily operation

The existing five scheduler slots retain one private-state writer. Active boards
are due once per EAT calendar day, with exponential failure backoff and server
cooldowns. `python -m ingest.main --employers-only --output-dir ...` refreshes
only approved employer collectors. Ordinary all-source runs include them too.
`python -m ingest.employer_watch --data-dir ...` monitors due unresolved pages,
checks shared registry URLs once, skips manual/retired/blocked sources, respects
robots and backs off failures. It never promotes discovery clues to jobs. The
tracked metadata seed avoids replaying the completed full probe on deployment.

Private state contains `employer-candidates.json`, `employer-watch.json`,
`employer-collection-metrics.json` and `employer-coverage.json`, plus dated coverage
reports. Failed extraction stays retryable even after a link disappears from a
bounded feed. Validation failures keep compact retry metadata. Only accepted
promotion marks candidates published; failed deployments retain operational
evidence without promoting canonical jobs. No descriptions are retained.

Structured collectors require reviewed pagination, permitted public hosts and
individual vacancy destinations. IDs use requisitions or persisted URL-to-UUID
mappings, never mutable titles. Conditional responses require separately reviewed
endpoint behaviour and cached vacancy metadata. PDF roles require durable IDs;
shared PDF links do not collapse different requisitions. Unsupported encrypted,
scanned, overlarge or ambiguous PDFs fail closed. No SmartRecruiters API collector
is enabled because the tested API robots policy disallows it.

Undated accepted jobs show a labelled First found date, used as a period-filter
fallback. Employer posting dates remain primary when supplied. Operational check
timestamps alone do not trigger builds. Source absence expiry remains disabled.
See the dated activation review for permissions and field-verification limits.
