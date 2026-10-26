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

NCBA initially passed local verification while inactive: 4 roles, 1 eligible technical role (Assistant Manager, ICT Risk; Tanzania; closes31October2026). Official employer pages provide the vacancy data and application entry points; blocked SuccessFactors collection is excluded. Stable provider jobIds plus a seeded surrogate UUID are used. The hosted checks and isolated trial subsequently passed, as recorded below.

## Verified delivery

NCBA is active after hosted M0 run40286880400, isolated trial40286993849 and production40287236820. One new validated vacancy is published: Assistant Manager, ICT Risk; Tanzania; closes31October2026.4roles fetched completely,3nontechnical excluded. Accepted private state05adec9, Company Career Page31, All Jobs2781. Local-build/live HTML identity and original-link checks passed;301Python tests and lint passed. No interactive browser verification is claimed.

Current configuration:23 functioning registry collectors linked to27 separate employer records;13 additional linked records relative to baseline14. These are registry coverage counts; they do not mean30 new collectors or100 completed companies. KCB was already active; the other28 supplied sources remain pending, blocked, failed or manual review.

## Follow-up extraction, access, and permission checks

Follow-up checked 26 October 2026. This section supersedes any older empty-page or extraction notes below where they conflict. Each accessible page was assessed for current role identity, location/date clues, stable listing/application links, and available access-policy evidence. Robots permission is not treated as a republication license. No source was activated or vacancy published from this follow-up.

| Employer | Latest extraction/access result | Permission and disposition |
|---|---|---|
| Kingdom Bank | Careers URL now returns an Incapsula challenge shell (`noindex,nofollow`); no role details extracted. | Do not bypass the challenge; pending. |
| Spire Bank | Page lists Senior Manager–Operations, Head of Legal, and Security Manager; no vacancy dates/details surfaced. Security Manager is not evidence of a technical role. | No automation permission established; pending. |
| Gulf African Bank | Two live Relationship Manager roles, both closing 28 October 2026; detail pages confirm SME sales and HNI relationship-management duties, not technical work. | Website terms reserve copyright and prohibit unauthorized misuse; no collection/reuse grant found. Manual permission review. |
| Sidian Bank | Current page lists Senior Relationship Officer–HNI and Senior Manager–Credit Analysis plus an open application; no technical vacancy found. | Recruitment privacy notice is not collection permission; pending. |
| Stanbic Bank Kenya | Group search page exposes Uganda Service Consultant roles, not a verified Kenya inventory. The public API route remains robots-blocked. | No API retry or alternate route; pending/blocked. |
| Muungano Microfinance Bank | October 2026 Manager Finance/Administration/Strategy advert is reachable; not a technical role. | No collection permission established; no collector. |
| I&M Bank Kenya | Adrenalin page remains an application shell. Browser loading failed and its robots endpoint returned an application error; no Information Systems Audit vacancy could be independently verified. | No alternate API or hidden route pursued; pending. |
| Postbank | Current page fetch shows only the careers slogan; the earlier explicit-empty result was not reproduced and no listing inventory is available. | Empty-state monitoring is not justified; pending. |
| Habib Bank AG Zurich Kenya | Relationship Officer/Manager role closed 10 November 2025; Security Manager closed 3 November 2025 and describes physical security/fraud operations, not cybersecurity. | Website terms do not expressly authorize vacancy collection/reuse; no current technical opening. |
| Sumac Microfinance Bank | Greenhouse board reports no openings, but employer-to-board linkage remains unverified; corporate site instead links a Relationship Officer role. | Do not infer official zero openings from the unlinked board; pending. |
| HFCB | Previous snapshot reported no positions; current extraction returned only page navigation/footer, with no vacancy inventory or explicit empty statement. | No working collector established. |
| LOLC Kenya Microfinance Bank | Visible roles are Collections/Recovery, Liability Sales, Management Accountant, and Business Development; no technical match. | No collection permission established; no collector. |
| UBA Kenya | Careers page lists 16 roles with linked PDFs, including Head, Digital Banking. Its PDF confirms the Digital Banking department but the role's technical duties, closing date, and a stable vacancy record were not verified. | Kenya robots file has no disallow rule, but the linked group terms page is challenge-blocked; permission unresolved. |
| Victoria Commercial Bank | SnapStar robots explicitly allows public pages. Its sitemap lists four VCB postings. `Officer II - Cyber Security Analyst` is a clear technical role in Nairobi, posted 21 October and closing 27 October 2026; its stable detail page has JobPosting metadata. The other three are ESG risk and credit-administration roles. | SnapStar's FAQ/privacy routes surfaced no reuse terms. Public crawling is allowed by robots, but reuse permission and official VCB-to-platform linkage remain unconfirmed; candidate only. |
| Rafiki Microfinance Bank | Visible adverts are Relationship Officer–Business Development and Senior Officer–Marketing/Branding; no technical role. | No collection permission established; no collector. |
| SMEP Microfinance Bank | Careers page links Relationship Manager–Business Development and Risk & Compliance Officer (September 2026); no technical role established. | Robots endpoint returned an error; linked customer terms do not establish collection permission. |
| Standard Chartered Kenya | Kenya-filtered search remains a shell with no extracted jobs or completeness/pagination evidence. | Filter retained; no API or alternate route approved. |
| Premier Bank Kenya | Current job page explicitly says there are no job openings. | Empty state only; not counted as a vacancy collector. |
| Kenya Women Microfinance Bank (KWFT) | Recruitment hostname still has a DNS/access failure; no listing data. | Backoff retained; no bypass. |
| M-Oriental Bank | Current official page now lists a Digital Solutions & Full Stack Developer role, plus nontechnical roles. The technical role has no posted/closing date, location, or role-specific URL; applications are directed to email. | Robots allows public site paths, but terms/privacy URLs returned 404 and no explicit collection permission was found. Candidate pending; do not publish without field and permission review. |
| Umba Microfinance Bank / Umba Kenya | Prior access restrictions and manual review remain in force. | No retry; manual permission review. |
| SBM Bank Kenya | Manager, Core Systems is technical and closes 28 October 2026, but the listed location is only “Head Office.” | Terms prohibit storing, reprocessing, reusing, or distributing site content without permission. Manual permission required; no collector. |
| Paramount Bank | Careers page shows Engineering and Product Design headings but no individual vacancy. | Department headings are not jobs; pending. |
| Salaam Microfinance Bank | Careers URL redirects to a suspended-host page; no vacancy content. | No collection; pending access. |
| National Bank of Kenya | Earlier page response contained only generic careers navigation; the follow-up request failed at transport level. No advert was extracted. | Access and completeness unresolved; pending. |
| Prime Bank | Careers path remains disallowed by robots. | Blocked; no bypass or retry. |
| U & I Microfinance Bank | Current open position is Assistant Marketing Manager; nontechnical. | No collection permission established; no collector. |
| Middle East Bank Kenya | Current official page explicitly says there are no vacancies. | Empty state only; not counted as a vacancy collector. |

The 28 checks exclude the already-active KCB source and the NCBA source. NCBA Insurance and Loop Payco remain distinct employer records and are not counted as covered merely because they share NCBA's careers URL. Two newly confirmed technical candidates surfaced (Victoria Commercial Bank and M-Oriental); neither passed all permission, source-linkage, or field-completeness gates. SBM's Manager, Core Systems remains a known technical posting blocked on explicit permission. UBA's Head, Digital Banking remains unclassified pending role-body extraction. Registry coverage therefore remains 23 active collectors / 27 linked employer records / 13 additional linked records versus the 14-record baseline.

### Evidence corrections and collector follow-through

The bounded28-source metadata results are saved in `../bank-deep-review-2026-10-26/`. I&M was independently verified in a fully loaded browser:5jobs, including Assistant Manager Information Systems Audit, Nairobi, posted23October and closing2November2026. The public ATS itself returned200; it was the subsequent corporate linkage/policy request that returned403. Do not call this an empty or blocked ATS. Standard Chartered loaded3Kenya banking/wealth roles, all nontechnical; the initial No jobs found state was temporary. Kingdom returns a212-byte Incapsula challenge to HTTP; do not bypass it.

VCB official employer linkage is now confirmed: the bank homepage CAREERS link points to `https://snapstartalent.com/vcb`. Provider robots expressly opens public vacancy pages to crawlers and supplies the sitemap. The four scoped sitemap roles match the four fully loaded UI cards; each detail exposes provider IDs, explicit Nairobi location, original role/application URL and dated JSON-LD. A reusable namespaced sitemap parser now validates the complete XML before declaring a healthy empty board, rejecting HTML challenges, sitemap indexes and malformed entries. No descriptions or candidate/account pages are retained. Local M0 passed4roles/1eligible cybersecurity job. Hosted verification and trial are next; VCB remains inactive until those gates pass. Reviewed date-only deadlines use end-of-day Africa/Nairobi.
