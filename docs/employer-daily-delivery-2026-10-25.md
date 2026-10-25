# Daily employer collection delivery — 25 October 2026

Production revision: `fcc8ca097186f5b48ee108f3137826d9835dfdf2`.
[Validation 40203924241](https://github.com/kimtour/techjobs-africa/actions/runs/40203924241)
passed 269 Python tests, 14 frontend tests and 17 scheduler tests, lint, Astro
validation/build and scheduler deployment dry-run.

[Isolated hosted trial 40203795837](https://github.com/kimtour/techjobs-africa/actions/runs/40203795837)
completed all five approved boards and found two additional eligible vacancies.
[Production run 40204044721](https://github.com/kimtour/techjobs-africa/actions/runs/40204044721)
fetched the five sources successfully, published the site, promoted accepted data,
and saved its audit in the private data repository (revision `6006162`).
Deployment: https://aa398b7d.techkazi.pages.dev/.
Live: https://techkazi.pages.dev/.

## Actual results

- 107 employer posting records checked; 105 filtered and two published.
- Both additional jobs are M-KOPA backend roles in Johannesburg, South Africa.
  Source posting dates are 9 October and 30 September; these are reviewed current
  inventory, not jobs newly posted today. They do not prove Kenya eligibility.
- Company Career Page contains 16 accepted direct-employer vacancies (14 existing
  plus two additional). All Jobs contains 2,762 unique accepted vacancies.
- Five of 758 registry employers have configured daily vacancy collection and
  completed a successful vacancy check today. Existing direct feeds also continue;
  this registry coverage measure does not count them as newly integrated employers.
- All 758 employers and 633 recruitment sources have explicit coverage records.
  Source outcomes: five reviewed complete baselines, four awaiting verification,
  59 blocked, 45 manual, 520 without a reviewed supported vacancy collector.
  Baseline runs record `no_new_jobs`: initial inventory is not labelled new.
- Unresolved-page monitoring made zero new requests on deployment day because the
  full-list probe seed already covered that day. On subsequent days due pages are
  staggered across the existing slots, subject to discovery budgets and backoff.
  Page monitoring is not complete vacancy collection.

Private reports: `state/employer-coverage.json`, dated JSON under
`state/employer-coverage/`, `state/employer-coverage.md`, candidate ledger,
collection metrics, source health and publication history. Published candidates
are marked published only after accepted promotion; both candidate rows were
verified in that state.

## Browser and output checks

Local and live desktop/mobile checks confirmed Company Career Page immediately
after All Jobs, initial 10 rows/loading 16, preserved feed scroll (1,178px) and
unchanged other feeds' document positions, scroll and state. Day produces an empty
company feed with working recovery; Latest restores 10. Month shows five current
matches. At 390px, ordering is unchanged, bodies are 383px and there is no horizontal
overflow. Desktop bodies are 415px. Employer filtering finds the two M-KOPA jobs;
direct-employer filtering counts 16 unique vacancies, without doubling shared cards.
HTML verification matched every accepted job identity, company-feed membership,
original application destinations, publisher labels and site metadata/assets.

## Remaining coverage limits

This delivery implements the daily framework, not working vacancy extraction
from all 758 companies. The 520 unsupported sources still need reviewed extraction
mappings and evidence. Four ATS leads await verification. Manual/blocked sources
require access or permission review; terms restrictions are not bypassed through
alternate APIs. See the dated activation review. Generic structured/PDF collectors
are implemented and tested, but have no unreviewed sources activated.

No descriptions, access tokens or full page responses were persisted. No source
absence expiry was enabled; no failures closed jobs. No changes were made to
billing limits or the five scheduler slots. Public standard runners execute the
pipeline; private state remains private with one writer.
