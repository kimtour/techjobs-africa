# KCB Oracle board review — 25 October 2026

## Scope

Verify the official KCB Bank Kenya Oracle Candidate Experience board for
collection of factual vacancy metadata only. This review does not assert a
redistribution licence.

- Employer source: `employer_a89e7ddc7350f19e`
- Official careers page: <https://ke.kcbgroup.com/careers>
- Board: <https://eoin.fa.em3.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_3001/jobs>
- Listing endpoint: <https://eoin.fa.em3.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions>
- Identity: immutable Oracle requisition ID
- Expiry from absence: disabled

## Local and hosted evidence

The local M0 crawl recorded nine vacancies and passed official-link, stable-ID,
application-link, location, date-review, and completeness checks. Its source
artifact is `discovery-output/employer-api-m0-local-2026-10-25/employer_a89e7ddc7350f19e.json`.
The local robots check allowed the official KCB careers path; the Oracle host
returned 404 for `robots.txt`, which is not a disallow rule.

Hosted discovery run
[40213034476](https://github.com/kimtour/techjobs-africa/actions/runs/40213034476)
also completed all nine vacancy records. The hosted report marked official
linkage, stable IDs, application links, locations, dates, and completeness true.
KCB's official robots file returned 200 and allowed the careers page. The
Oracle-host `robots.txt` returned 404; the public board and listing endpoint
were accessible, with no robots disallow observed.

A fresh local fetch using the production adapter returned nine records,
completed pagination, and classified two records as eligible African technical
roles:

| Requisition | Role | Location | Eligibility | Application |
|---|---|---|---|---|
| 6700 | Senior Manager IT Applications & Asset Management | Kenya | CONFIRMED | <https://eoin.fa.em3.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_3001/job/6700> |
| 6688 | Risk Department, Uganda.IT Risk Analyst | Uganda | CONFIRMED | <https://eoin.fa.em3.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_3001/job/6688> |

## Terms and handling

KCB's careers page links its [Product Terms and Conditions](https://ke.kcbgroup.com/terms-and-conditions)
and [Data Privacy Policy](https://ke.kcbgroup.com/data-privacy-policy). The
accessible terms concern KCB products/accounts; the privacy statement governs
personal data. No automated-collection prohibition was identified in the
accessible material, and no redistribution licence is asserted. The collector
stores only factual role metadata, location, source dates, and the original
application URL. It does not retain job descriptions, applicant data, or
recruiter contact details.

This source is `verified` only. Production activation still requires an
isolated hosted trial and review of its candidate output against the accepted
jobs before publication.
