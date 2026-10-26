# Official bank portal repairs — 26 October 2026

## Completed repairs

| Employer | Correction | Delivery |
|---|---|---|
| M-Oriental Bank | Recovered provider IDs and explicit role-specific Nairobi locations from four public job cards; verified each ID against the public WordPress career records and the developer's individual job page. Reviewed the actual privacy URL. | Daily collector active; one developer vacancy published. |
| I&M Bank | Confirmed that the official [career page](https://www.imbankgroup.com/ke/career-page/) links to the existing Adrenalin tenant. The tenant URL was correct; official linkage evidence was missing. | Official-link gate repaired; complete API/collector/policy/trial verification remains pending. No jobs claimed published. |
| Sumac | Replaced unlinked Greenhouse URL with the [official employer careers portal](https://sumacmicrofinancebank.co.ke/vacancies/); removed the stale Greenhouse pilot suggestion. | Corrected source remains inactive. Inspected grouped relationship-officer advert dated September2025; no eligible technical job verified. |

The [official M-Oriental page](https://www.moriental.co.ke/careers/) provides the role-specific location. Numeric provider ID6728 remains stable when titles change; the functional employer post URL resolves to the original individual job page and HR application details. The collected template does not display posting/closing dates, so first-found is labelled separately. CMS publication timestamps are retained only as discovery evidence, not invented as newly posted dates.

## Verification and delivery

Local and hosted M0 read all four records completely; hosted run40299508802 passed. Isolated trial40299976981 found one additional eligible Nairobi developer listing and excluded three nontechnical records. [Production40300532700](https://github.com/kimtour/techjobs-africa/actions/runs/40300532700) succeeded and persisted private state625c845. Company Career Page33 / All Jobs2,793; local-build/live HTML acceptance passed for every job identity, original link, feed order and site metadata/assets.314Python tests and lint passed. No interactive browser acceptance is claimed. No descriptions, candidate forms or applicant data are persisted; source absence expiry remains off.

The earlier user-requested all-feed refresh40295869509 also completed:34successful sources, Google/JSearch skipped at its monthly quota, Expertini skipped for access restrictions;9jobs added. Scheduled run40296307554 subsequently completed, followed by the targeted M-Oriental publication.

## Restrictions retained

The regulator's Salaam directory still names the supplied bank domain; no replacement careers portal was established. SalaamPay is a banking app, not a careers feed. KWFT's official homepage still links to its DNS-failing Conquest recruitment hostname. Prime's indexed official page says no vacancies but its robots restriction remains. Kingdom's Incapsula and Stanbic's API restrictions were not bypassed. Web search does not grant collection permission or make expired adverts current.

Current registry progress:25active collectors,27verified employer records,13additional versus the14-record baseline.29linked records include two unverified NCBA discovery links; those are excluded from verified coverage. The100-company target remains incomplete.
