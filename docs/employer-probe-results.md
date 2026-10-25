# Employer collection coverage — 25 October 2026

Full-list metadata discovery only. No production state or source lifecycle was
changed. No vacancies were published by this probe.

- Employer records: **758**; imported rows: **796**.
- Recruitment sources assessed: **633**; attempted: **593**; manual/skipped: **40**.
- Verified active daily employer collectors: **0**. Five sources remain in trial.

| Discovery outcome | Sources |
|---|---:|
| Reachable; metadata discovery completed | 476 |
| Blocked/access-limited | 57 |
| Failed (transport, DNS or HTTP error) | 59 |
| Manual-only / skipped | 40 |
| Partial (probe limit) | 1 |

| Primary method hint on reachable pages | Sources |
|---|---:|
| ATS provider/embedded-board clue | 65 |
| Feed link | 144 |
| PDF link | 61 |
| Possible vacancy links for listing comparison | 42 |
| JobPosting structured data | 1 |
| Needs further investigation | 163 |

Method hints are provisional, mutually exclusive and ordered by detection
priority. A feed can be a blog feed, a PDF can be a non-vacancy document, and an
ATS link does not verify employer attribution, access permission, pagination or
eligibility. These counts rank investigation; they do not measure job coverage.

Provider clues: Oracle 10, JazzHR 9, Workday 9, Greenhouse 7, Workable 6,
SmartRecruiters 5, Taleo 5, Lever 4, Manatal 4, Ashby 3 and Breezy 3.
The 17 Ashby/Greenhouse/Lever/Breezy hints are the first review queue because
reusable trial connectors already exist. They include the five trial portals.

The initial probe exposed a compressed-response decoding bug. After correction
and regression testing, only the 462 affected records were rechecked. Existing
blocked/failed/manual outcomes were retained, and the final report contains no
compression errors. The corrected invocation used 995 requests and 195.41 seconds;
this is discovery work, not a forecast of full daily vacancy-collection runtime.

The local ignored `discovery-output/employer-probe-2026-10-25/coverage.json` contains one row for every employer; `companies.csv` is the compact
review sheet; `sources/` contains the source-specific discovery evidence. A
reachable page is not a successful complete vacancy check and never means
"no new jobs". No unsupported/failed source is counted as daily coverage.

Next: review provider clues and collection permission, test new/changed-job
extraction in isolation, then activate reviewed sources in the existing pipeline.
Keep retryable extraction state, true posting dates separate from first-found
dates, stable identities, one state writer and source-specific failure backoff.
