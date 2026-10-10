# Missing LinkedIn comparison roles — 10 October 2026

The supplied screenshot is evidence of a coverage gap, not an instruction to
scrape LinkedIn or assume every result is Kenya-eligible. The current accepted
data branch has 1,329 jobs. Other M-KOPA backend roles exist, but the exact
Mobility (12 month FTC) vacancy and the other three screenshot titles are absent.

## Findings and correction

| Screenshot title | Finding | Correction |
| --- | --- | --- |
| Senior Backend Engineer - Mobility (12 month FTC) | Title already passes. Employer board was not configured. | Verified employer careers page links the `M-KOPA` Ashby board; reuse the existing documented API adapter. Native ID `121d269d-f893-4e4c-9a88-eae3f6c5c917`, Nairobi, Remote, published 9 October 2026. |
| GCP Cloud Platform Administrator | Title was rejected; Google queries only searched software engineering. | Add the precise cloud administration phrase and a dedicated Kenya discovery query. Actual SDG vacancy and location still require provider/employer evidence. |
| Software Developer Trainee | Title already passes. Employer/source coverage is missing. | Retain software discovery; no title-filter expansion needed. Screenshot alone does not verify Kenya eligibility. |
| Manager,Technology | Comma and reversed role/domain order prevented a match. | Normalize title/keyword separators consistently; add `manager technology` and a Kenya technology-management discovery query. Exact BRAC vacancy is still unverified. |

Public employer evidence: https://www.m-kopa.com/careers embeds
https://jobs.ashbyhq.com/M-KOPA . Local API discovery returned 34 listed jobs.
Only explicit Kenya locations, including secondary locations, are accepted for
this employer source. UK/European variants remain excluded. Remote metadata and
the employer name are preserved. Non-technical telesales QA is rejected.

Local sanitized API discovery: `python -m ingest.ashby_discovery --board M-KOPA
--output /tmp/techjobs-m-kopa-discovery.json`. Robots returned HTTP 401, so no
robots permission is inferred. This route uses Ashby's already documented public
posting API. Response descriptions remain in memory and are never saved.
The optional employer-board M0 workflow records the same minimal metadata from
a hosted runner; production activation is gated until that verification succeeds.

Google discovery gives each of four role/location queries a first page before
continuations, sharing five requests per Kenya calendar day and the existing
160-request monthly ceiling. Configured queries now drive production execution.
Broader queries improve discovery but do not guarantee LinkedIn's result set.
No new scheduler, direct LinkedIn scrape, fuzzy merge or invented posting date.

M-KOPA jobs appear in All Jobs and the existing fourth Other/Google/Linkedin feed,
with `M-KOPA via Ashby` attribution. Other source feeds retain their order,
independent periods, scrolling and load-more behavior.
