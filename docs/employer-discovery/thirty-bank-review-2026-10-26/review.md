# Thirty requested bank sources — 26 October 2026

All30 actual URLs were already in the source registry. No duplicate employer/source records were created. The unnamed no-URL row was skipped. This review does not activate unverified collectors or publish career pages as jobs.

| Employer | Outcome |
|---|---|
| Kingdom Bank | Careers shell reachable; loaded vacancy inventory not established. |
| Spire Bank | Reachable page does not establish a complete current vacancy inventory. |
| Gulf African Bank | Relationship manager openings observed; technical match not established. Full extraction/date review pending. |
| Sidian Bank | Senior Manager Credit Analysis observed; no technical match established. |
| Stanbic Bank Kenya | Group search shell reachable; official vacancy loading and country filtering unresolved. Prior API robots restrictions remain in force. |
| Muungano Microfinance Bank | Finance/administration/strategy manager advertisement observed; no technical match established. |
| I&M Bank Kenya | Adrenalin public application shell reachable; vacancy inventory and pagination not established. |
| Postbank | Official page explicitly reports no openings. Empty-state observation only; no verified vacancy collector. |
| Habib Bank AG Zurich Kenya | Relationship and Security Manager titles observed; physical-security title is not presumed cybersecurity. Field and date review pending. |
| Sumac Microfinance Bank | Supplied Greenhouse page is empty but official employer-to-board linkage not verified. Official corporate vacancies page instead links a Relationship Officer post. Do not activate or infer zero official vacancies from empty unlinked ATS. |
| HFCB | Official page explicitly says no open positions. Empty-state observation only; no verified vacancy collector. |
| LOLC Kenya Microfinance Bank | Collections/recovery management openings observed; technical match not established. |
| UBA Kenya | Open-vacancy documents require individual title/date/location/identity review. |
| Victoria Commercial Bank | SnapStarTalent public application shell reachable; full vacancy loading and fields unverified. |
| Rafiki Microfinance Bank | Careers page reachable; vacancy extraction and dates require review. |
| SMEP Microfinance Bank | Careers documents require individual PDF title/date/location/identity review. |
| Standard Chartered Kenya | Country-filtered public search shell reachable; actual inventory and pagination unresolved. Kenya filter preserved. |
| Premier Bank Kenya | Jobs page reachable; role identity/date/completeness review pending. |
| Kenya Women Microfinance Bank (KWFT) | Recruitment hostname DNS resolution failed; vacancy availability unknown. Discovery backoff retained. |
| KCB Bank Kenya | Existing active KCB Oracle collector retained; no duplicate. |
| NCBA Bank Kenya, NCBA Insurance (formerly AIG Kenya), Loop Payco | Assistant Manager ICT Risk is explicitly Tanzania, closing31October2026. Original SuccessFactors application URL observed, but its collection path robots disallows access. Employer-owned detail extraction under review; no Kenya inference. Shared employer records kept separate. |
| M-Oriental Bank | Official page explicitly reports no positions. Empty-state observation only; no verified vacancy collector. |
| Umba Microfinance Bank, Umba Kenya | Existing manual permission review retained; previously observed automation restrictions not overridden by resubmitted URL. |
| SBM Bank Kenya | Manager Core Systems advert closes28October2026, job location Head Office only. Terms explicitly prohibit storing/reprocessing/reutilising/distributing website content without permission. Manual permission review; no production collection. |
| Paramount Bank | Careers page reachable; Engineering heading alone is not a validated vacancy. |
| Salaam Microfinance Bank | Careers page reachable; vacancy extraction and dates require review. |
| National Bank of Kenya | Official careers page reachable; advert extraction/date/completeness review pending. |
| Prime Bank | Careers collection disallowed by robots. Blocked; no bypass. |
| U & I Microfinance Bank | Career documents require individual title/date/location/identity review. |
| Middle East Bank Kenya | Official page explicitly reports no vacancies. Empty-state observation only; no verified vacancy collector. |

Initial page checks: {"REVIEWED_PAGE": 26, "FAILED": 1, "ALREADY_ACTIVE": 1, "PERMISSION_REVIEW": 1, "BLOCKED": 1}. Reachability does not prove collection.

Progress at initial review was10 additional linked employer records; the deployment below updates that snapshot. NCBA subsequently completed all checks and was activated; see delivery receipt below. SBM requires permission.

NCBA now has an inactive, locally verified HTML collector:4 roles,1 eligible technical role (Assistant Manager, ICT Risk; Tanzania; closes31October2026). Official employer pages provide the vacancy data and application entry points; blocked SuccessFactors collection is excluded. Stable provider jobIds plus a seeded surrogate UUID are used. Hosted checks and isolated trial remain required before production.

## Verified delivery

NCBA is active after hosted M0 run40286880400, isolated trial40286993849 and production40287236820. One new validated vacancy is published: Assistant Manager, ICT Risk; Tanzania; closes31October2026.4roles fetched completely,3nontechnical excluded. Accepted private state05adec9, Company Career Page31, All Jobs2781. Local-build/live HTML identity and original-link checks passed;301Python tests and lint passed. No interactive browser verification is claimed.

Current configuration:23 functioning registry collectors linked to27 separate employer records;13 additional linked records relative to baseline14. These are registry coverage counts; they do not mean30 new collectors or100 completed companies. KCB was already active; the other28 supplied sources remain pending, blocked, failed or manual review.
