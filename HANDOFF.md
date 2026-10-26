# TechKazi continuation handoff

Updated: 25 October 2026, Africa/Nairobi.
Workspace: `/Users/kim/Documents/techjobs-africa`.
Live: https://techkazi.pages.dev/.

## User intent and authority

Collect individual technical vacancies daily across all 758 employer records.
Publish actual jobs with original application links, not a careers-link directory.
Company Career Page follows All Jobs. The user approved public code, deployment
after checks, excluding Ministries and departments, and retaining verification
gates. Latest request: implement everything. Do not request those approvals again.

## Storage and operation

- Public code: `kimtour/techjobs-africa`, `main`.
- Private accepted state: `kimtour/techkazi-data`, branch `data`. Actions disabled
  there. `.github/actions/checkout-data` uses scoped `DATA_REPO_SSH_KEY` and
  `DATA_REPOSITORY`; never fetch state from the public code repository.
- All state writers share `techjobs-pipeline` concurrency in the code repository.
  Do not add independent writers, force-push state or delete scheduler claims.
- Original data history and 418 old artifacts were backed up privately before
  public exposure. Public workflow recovery audit is encrypted on persistence
  failure. Never expose secrets or private state in public artifacts/logs.
- Existing Cloudflare scheduler keeps five EAT slots: 06, 09, 12, 15, 19.
  Dispatch does not prove a fetch ran. Standard public-repository hosted runners
  are the implemented quota solution; private state does not run its own CI.

## Registry and coverage

Workbook excludes Ministries and departments: 796 rows, 758 employers, 633
recruitment URLs. Employer identity remains separate from shared fetching URLs.
`config/employers.yaml` and `config/employer-sources.yaml` are generated/reviewed
registries; the spreadsheet is not a production runtime input.

Full metadata probe: reachable 476, blocked 57, failed 59, manual 40, partial 1.
These are page-access outcomes, not 758 working vacancy collectors. Its 65 ATS
clues require review. Seed `config/employer-discovery-seed.json` prevents replaying
the initial probe and blocked sites on first deployment.

Five sources are approved active with reviewed initial inventory: M-KOPA
`employer_58b8d22cf280a524`, Jumia `employer_6123edf0db94e3a1`, Turaco
`employer_3d2a408f9d01331a`, Ampersand `employer_1a047fd979fcdf88`, Tala
`employer_9e1960f0be135be5`. All nine verification checks plus trial/publication
reviews remain mandatory. Fresh local and hosted isolated trial run 40203795837
completed all five, yielding two additional eligible M-KOPA jobs in South Africa.
Zero technical/eligible jobs on other boards is not a parser failure.

Additional local ATS checks: Wasoko, GiveDirectly, Andela, pawaPay, Sama, Unlimit,
LemFi. GiveDirectly/Andela/pawaPay/Unlimit terms restrict automated use and/or
republication; manual until permission. LemFi terms returned 403; manual pending
review. Sama remains pending collection basis/hosted verification; Wasoko's empty
board cannot verify location fields. Moniepoint/Busara remain blocked.
SmartRecruiters API robots disallow collection: no API collector is enabled.
Kijabe's three nontechnical JSON-LD roles lack durable role IDs/destinations.
See `docs/employer-activation-review-2026-10-25.md` for evidence/terms links.
No messages to employers have been sent or authorized.

## Implemented collector framework

Commits `5611262` (collection framework) and `fcc8ca0` (staggered scheduling).

- Reusable Ashby, Greenhouse, Lever and Breezy collectors; reviewed JSON-LD,
  RSS/Atom, custom field mappings and multi-role PDF collectors.
- Stable requisition IDs or persistent URL-to-UUID mapping; never title IDs.
- Retryable compact candidates, first-seen persistence, conditional requests only
  after endpoint review, full pagination, per-path/redirect robots checks and
  public-host validation. LinkedIn/Facebook collection forbidden.
- Initial silent baseline by default. Five reviewed pilots explicitly permit
  current inventory. Initial inventory is never labelled newly posted.
- Separate seen/extraction/validation/published states. Failed detail extraction
  stays retryable after links leave bounded feeds. Promotion alone marks published.
- Source posting, first found, closing and last checked dates remain distinct.
  Undated jobs use labelled First found as the display/filter fallback.
- Distinct PDF requisitions sharing an apply URL do not merge. Employer links
  win exact cross-source dedupe and attribution survives. No fuzzy auto-merges.
- Daily source-ID hash spreads work across existing slots; missed work can catch
  up later. Failure backoff/cooldowns remain enforced.
- Separate discovery budget: up to 150 sources/run, 12 requests/source; blocked,
  manual and retired sources skipped. Page monitoring never publishes jobs.
- Private daily reports include all employers, configured coverage, actual
  complete checks, new/no-new/partial/failure/blocked/manual/unsupported outcomes,
  review gaps, and pending candidates. Check timestamps alone do not rebuild.
- Descriptions never persist; technical and eligibility classification use them
  in memory. No EMEA-to-Kenya inference. New-source absence expiry stays off;
  failures and single 404 responses cannot close jobs.

## Validation and publication status

Final hosted validation 40203924241 passed 269 Python tests, 14 frontend
and 17 scheduler tests, lint, Astro check/build and scheduler dry-run.
Targeted collection/registry tests passed 23 tests.
Local desktop/mobile browser checks with real shadow data: Company Career Page
second, 16 jobs, All Jobs 2762, independent controls, empty Day recovery, bounded
Month filtering, 415px desktop/383px mobile bodies, no 390px overflow.

Production employer run 40204044721 succeeded for revision `fcc8ca0`, deployed
https://aa398b7d.techkazi.pages.dev/ and promoted private data revision `6006162`.
Accepted and live counts: Company Career Page 16, All Jobs 2762. All five source
checks succeeded; 107 records checked, 105 filtered, two M-KOPA rows published.
Local and live browser checks and full HTML identity checks passed. Live feed
loading preserves scroll and other feeds; 390px mobile has no overflow.
Coverage: 758 employers/633 sources; five configured and successfully checked
employers. Source outcomes: 520 unsupported, 59 blocked, 45 manual, four awaiting
verification, five healthy initial baselines. Full collection is still incomplete.
See `docs/employer-daily-delivery-2026-10-25.md` for the complete receipt.

## Evidence and continuation

- `docs/daily-employer-collection.md`: implemented operation and remaining limits.
- `docs/source-panels.md`: local/live browser acceptance contract.
- `docs/employer-probe-results.md`, `docs/employer-pilot-results.md`.
- `docs/free-execution-and-private-state.md` and `PROJECT_CONTEXT.md`.
- Local probe `discovery-output/employer-probe-2026-10-25/`.
- Local shadow `/tmp/techkazi-daily-employer-shadow-20261025` (never promote manually).
- Hosted trial download `/tmp/techkazi-hosted-daily-trial-40203795837/`.
- Private clone `/tmp/techkazi-private-state` (pull before interpreting as current).

Full vacancy coverage remains incomplete. Hundreds of custom pages require
individual extraction/permission review; reachability is insufficient. Expand
only through recorded M0 local/hosted checks, isolated trial, then publication
review. No proxies, evasion, robots overrides or unreviewed automatic activation.
Preserve unrelated `.vscode/` and `_build/` files.

### Vacancy-first expansion batch — 25 October 2026, 22:25 EAT

- The 758-employer goal remains unfinished. Broad read-only vacancy assessment checked 34 supported portals representing 37 employer leads: initially 23 complete, six partial and five failed. Old Mutual subsequently completed the larger bounded crawl. The report is `docs/vacancy-priority-2026-10-25.md`.
- Activated three reviewed daily collectors: Absa Group (7 eligible jobs), Old Mutual Group (2), NRC (1). Group labels are used; employer records remain separate. These ten openings are in South Africa and Uganda. No new-source absence expiry enabled.
- Hosted M0 `40224885754` passed Absa/NRC; Old Mutual corporate site returned 403. Independent public ATS check `40225142022` passed after locally evidenced official linkage and collection review. No blocked corporate request was retried or bypassed. Hosted trial `40225342690` produced ten additional application URLs absent from accepted state.
- Production `40225632030` on `9003f35` succeeded; private state `cf2f7dd`. Company Career Page: 33 (previously 23); All Jobs: 2,781. Local-build/live automated acceptance checked all job IDs, second-feed placement, original links and site metadata/assets. No interactive browser check is claimed.
- 289 Python tests and lint passed. Discovery and independent access checks now include eligible-job counts and metadata without another network fetch or production promotion.
- Preserve original checkout `/Users/kim/Documents/techjobs-africa` expansion WIP; do not overwrite its pending-source configuration with the remote state. The current clean code/config is in this managed worktree and remote main. The three earlier agents stopped with workspace-credit errors; their unfinished changes remain in the original checkout.
- Next priorities from actual openings: Safaricom/M-PESA (2 candidates, official-site hosted verification blocked), Pesapal (1, completeness/linkage unresolved), Unilever (1, verification unresolved); Ecobank (1) remains behind permission review. Do not count these as published or activate them from probe evidence alone.

### Continuation and requested banks — 26 October 2026

- User requested at least100 additional companies; target remains unfinished. Keep functioning vacancy collectors separate from page-state monitors and pending leads. Baseline before this overnight request:12 registry collectors /14 linked employer records.
- Added9 reviewed daily collectors (21 registry collectors now configured): Abt, CloudFactory, ControlRisks, Sama, Wasoko, PendaHealth, KenyaRedCross, NovaPioneer, OpenCapital. Local + hosted access40277293994 and isolated trial40277709967 passed. All9 had0 eligible technical jobs; no jobs manufactured. Activation main ab1ea25. Production40278312976 is in progress after scheduled40277362854 completed. Inspect existing runs; do not dispatch duplicates.
- Specific bank request handled in main5fef129: Absa alreadyactive, exact Kenya filter retained as lead metadata and checked through public Workday API.3 Kenya openings (CreditAnalysts – DigitalCredit, LegalCounsel, LeadGenerator),0 classified technical. One shared full-board collector retained; no duplicate fetcher and no loss of other African roles. ABCBank explicit0openings gets fail-closed daily empty-state monitoring; pending source is not counted as full collector. AccessBank returned automated access limit; markedblocked, no evasion. See docs/employer-discovery/three-bank-review/.
- Heartbeat automation techkazi-100-company-expansion ACTIVE in this chat, every30minutes. It should continue meaningful reviewed batches, remain quiet without actionable change, and pause when100 additional verified companies actually achieved. No guarantees of100 were made.
- All3 subagents again failed with workspace-credit limits. Their evidence remains under overnight-* directories. Do not repeatedly restart them without a funding change.
- Current uncommitted Pezesha proposal source employer_f3e0064cbce58d03 links formerly unmapped emp_9044c182049cf8d6. The10-role local M0 succeeded at /tmp/techkazi-pezesha-m0-local,5 technical/2 eligible KenyaDataScientist candidates.9 seededURL UUIDs plus a seeded expired consultancy URL give stable surrogate IDs, explicitly not employer requisition IDs. Locations were repaired to read nestedHTML. Strict human-date parsing is implemented and tested (26 collection tests passed) but NOT yet committed. Verify the explicit30November2025 consultancy deadline before approving; no source activation until hosted access and trial pass. Do not permanently exclude expired slugs; all10 are parsed. Draft config/employers.yaml, config/employer-sources.yaml, adapter and tests remain dirty for this work only.
- Next proposed jobs: Pezesha2; BURN has1 clear KenyanInformationSecurityLead but genericCarbonProjectManager/ProjectManagerIntern false positives require technical-duty review before activation. Paystack13-role localM0/7eligible exists, but terms include a broad data-republication restriction; resolve scope/permission rather than assume accessibleHTML/RSS means permission. Agent PDF and other custom proposals are unfinished.

### Six more bank URLs — 26 October 2026,09:24 EAT

- All six already existed in registry; updated their review/state, no duplicate source records. BOAKenya: explicit no-current-openings marker, daily page monitoring only. BankofBaroda: connection timeout, pending/backoff, availability unknown. BankofIndia and CBKOracleCX_2: HTTP403, markedblocked with no automatic evasion/retry. Branch: existing active shared collector rechecked11roles/3technical/0eligible. Caritas: current LegalOfficer2026 closes30October; other displayed adverts closed21October,20September,15September. No jobs published from these six. Evidence docs/employer-discovery/six-bank-review-2026-10-26/.
- The9-source production run40278312976 SUCCESS and private data7ae3452; all9 new sources healthy+complete and0newjobs. Current accepted totals measured:2,778AllJobs and28direct/legacyCompanyCareerPage jobs. Daily scheduled expiry/updates changed existing inventory; the9 zero-result collectors did not invent jobs. docs/company-expansion-progress.json records baseline14employerIDs,23currently configured employer records across21registry collectors,9additional verified companies out of100requested. Monitors/blocked/pending are excluded.
- Pezesha pending work is now locally verified and committed as inactive: source employer_f3e0064cbce58d03,10raw/5technical/2Kenyaeligible. Explicit expired consultancy deadline verified2025-11-30T23:59:59+03:00; code parses reviewed human dates strictly, source has persisted seeded surrogate URL UUIDs. Full301Python tests and lint passed. Hosted access, isolated trial, publication review and activation are NEXT; do not claim these2jobs are live. M0local /tmp/techkazi-pezesha-m0-local; source review docs/employer-discovery/pezesha-review/.
- Automation techkazi-100-company-expansion remains ACTIVE to continue broader work. Read these newer bank/source states rather than re-activating blocked sites from old pending patches.

- Pezesha hosted access is now dispatched as40280225759 against commit8770c68; inspect its result/artifact before any repeat. The pending Pezesha draft/date parser and six-bank records are now committed. No source6bank job or Pezesha job has been claimed published.

### Fourteen further banks and Pezesha publication — 26 October 2026

- User supplied14 bank URLs and explicitly said skip the unnamed/no-URL final row. All14 already existed in registry; their review state is updated, not counted as newly functioning collectors. Evidence docs/employer-discovery/fourteen-bank-review-2026-10-26/. OldMutual remains active; Consolidated gets strict empty-state monitoring only. Citi search robots disallows collection (blocked); Ecobank requires permission review (manual). DevelopmentBank connection failed (pending/backoff). Other dynamic/HTML sources remain pending full extraction/field/pagination/permission verification.
- Actual technical leads: Co-opBank HeadAI(detail title and WPpost450754 observed, no actual field/body extraction yet; do not assume location/deadline); CIB ManagerITSecurity with role-card NairobiHQ and individualPDF; DIB AssistantManagerInformationSecurity closes30October2026 but no job-scope location/applicant proof was established. Programmer/network ads need dates. Choice has3 marketing/sales roles and UUID URLs; Nairobi header observed on sampled role, full collector/terms review pending. Credit haslegalPDF; no tech job established. DTB NoJobsFound is unverified UI result, not proven empty board. Equity is accessible dynamicTaleo search shell; future reusable collector could cover4 records but employer identities must remain distinct. Family/GTBank inventories unresolved.
- Pezesha hosted access40280225759 and isolated trial40281406759 passed;2 additional application URLs not in accepted baseline. Activated on156cd1f. Production40283036347 succeeded and persisted private144cbfa. JuniorDataScientist and SeniorDataScientist explicitly Nairobi,Kenya are now published. Local-build/live automated acceptance passed for all30CompanyCareerPage jobs and2,780AllJobs; source remains absence-off.
- Current progress:22active registry collectors,24 configured employer records,10additional verified records from baseline14 (target100additional still incomplete). Monitors/blocked/pending excluded. docs/company-expansion-progress.json is refreshed. No jobs published from the14-bank review; do not attribute Pezesha jobs to those banks. Automatic continuation remains enabled.

### Thirty further requested banks — 26 October 2026

- Reviewed all30 supplied URLs; all already in registry, unnamed placeholder skipped. Evidence docs/employer-discovery/thirty-bank-review-2026-10-26/. KCB remains active; Prime robots blocked; KWFT hostname DNS failed; Umba existing manual restriction retained. Four explicit empty statements recorded, not counted as complete collectors. Dynamic shells and PDF ads stay pending extraction/field/policy checks.
- SBM has Manager Core Systems closing28October2026, but its terms prohibit storing/reprocessing/reusing/distributing website content without express permission. Marked manual; no bypass. HeadOffice alone not Kenya job-location proof.
- Sumac supplied Greenhouse board empty, but corporate-to-board linkage unverified; official corporate vacancies instead link RelationshipOfficer. Empty ATS must not be interpreted as zero official jobs. Keep pending.
- NCBA employer-owned HTML collector prepared INACTIVE: local full4-role M0 succeeded;1 eligible ICT Risk job explicitly Tanzania, deadline31October2026. Original provider jobIds parsed from employer-published application links; compliance/privacy job without provider ID gets seeded surrogate UUID. Complete local fields checked, no descriptions retained. External SuccessFactors collection is robots blocked and excluded. NEXT: hosted discover, inspect artifact, isolated trial, publication review, activation and production/live/private validation. No NCBA job claimed published yet; shared employer records remain distinct.
- Current verified progress unchanged22 active registry collectors /24 employer records /10 additional against baseline14. This bank review is not30 functioning collectors. Prior original checkout remains preserved. Automation continues the100-company target.

- NCBA hosted full M0 run40286880400 SUCCESS on6e30e62, all4roles complete,1eligibleTanzania. Status verified, not active. Provider jobIds and seeded UUID identical locally/hosted. Next isolated trial, then explicit publication review before activation.

- NCBA isolated trial40286993849 SUCCESS:4raw/1technical/1eligible/1additional unique application URL,3nontechnical withheld. ICT Risk externalID4069 explicitly Tanzania; deadline2026-10-31T23:59:59+03:00. Hosted CI40286985105 passed. Approved activation after review; next production through accepted private state/live checks. No source absence expiry.

- NCBA production40287236820 on37d3e2d SUCCESS; accepted private05adec9.4roles healthy+complete,1new ICT Risk vacancy published (externalID4069,Tanzania,deadline31October2026). CompanyCareerPage31 /AllJobs2781 verified against local build and live HTML, second-feed placement, all identities and original links plus canonical/favicon/robots/sitemap.301Python tests and lint passed; no interactive browser claim. Receipt docs/employer-discovery/thirty-bank-review-2026-10-26/ncba-production-receipt.json. Registry coverage now23active collectors /27linked employer records /13additional linked records versus14baseline. This is1new collector from30reviewedURLs, not30collectors; target100remains incomplete.
- Follow-up extraction/access/permission checks for the remaining28 bank URLs are recorded in docs/employer-discovery/thirty-bank-review-2026-10-26/review.md. Victoria Commercial Bank's public SnapStar sitemap exposes a Nairobi Cyber Security Analyst II closing27October; M-Oriental currently lists a Full Stack Developer role. Neither passed every permission/linkage/field gate, so no activation or publication occurred. Do not count these as collectors or new verified companies. NCBA Insurance and Loop Payco remain separate employer identities; the NCBA collector does not automatically cover them.

- Remaining28 bank checks now have bounded metadata evidence docs/employer-discovery/bank-deep-review-2026-10-26/. Earlier follow-up prose under-reported loaded dynamic portals: I&M browser shows5jobs including Nairobi InformationSystemsAudit339(closes2November), but corporate home403 prevents completed linkage/policy gate; StandardChartered browser loads3nontechnical Kenya jobs (not zero). Kingdom HTTP212-byte Incapsula challenge, no bypass.
- VCB official homepage CAREERS link to SnapStar /vcb is now verified. Public crawler statement + sitemap + four full JSON-LD roles reviewed; existing4-card UI count matches. Generic strict namespaced sitemap support implemented with malformed/index/empty/scope tests; optional reviewed date-only deadline timezone preserves end-of-day. Local M0 source employer_7a60d752d93bea48 SUCCESS4raw/1eligible Nairobi CyberSecurityAnalyst, providerIDVWNcMcxkEfMDTl99rZ2L, closes27October. Still INACTIVE: next hosted M0 and trial, then publication review/activation/production. Do not treat missing express licence as a permission grant; reviewed sources contain no identified automated public-vacancy-metadata restriction, and provider expressly permits public crawlers. No descriptions/private profiles/absence expiry.

- VCB hosted M0 run40293101361 on5a75c0c SUCCESS:4roles/1technical/1eligible, all checks pass. Status verified/inactive; next isolated trial. All310Python tests and lint passed locally and hostedCI40293088507. Scoped source tenant board vcb distinguishes future sitemap tenants while preserving employer identities. Per-source reviewed_source_checks now points to the detailed28-source evidence; no gate auto-activation. The expansion automation prompt was refreshed to remove stale Pezesha/NCBA pending instructions, retaining its30minute interval and quiet notification policy.

- VCB isolated trial40293441684 SUCCESS:4raw/1technical/1eligible/1additional unique vacancy absent from accepted baseline. Explicit Nairobi Kenya, posted21October, deadline27October2026 end-of-day EAT;3nontechnical filtered. Publication reviewed and activated after311Python tests/lint pass. Next production and accepted-private/live validation; do not claim live until confirmed.
- Coverage correction: NCBA source now explicitly verified_employer_ids for only its reviewed bank record; Insurance and Loop remain separate discovery links, not automatically verified coverage. Coverage computation honours this subset, with a regression test. Configured source links and verified company coverage must be reported separately; older27/13linked snapshots must not be repeated as independently verified totals.

- VCB publication40293787035 SUCCESS oncb08a35, accepted private9845e1f.4roles healthy+complete;1new Nairobi CyberSecurityAnalyst posted21October, closes27October end-of-day EAT. LiveCompanyCareerPage32/AllJobs2782 and local-build/live HTML checks passed;311Python tests/lint passed. Browser control unavailable at delivery, so no interactive acceptance claim. Receipt docs/employer-discovery/vcb-review/production-receipt.json.
- Final coverage audit found private daily_coverage had a second counting path; it now honours verified_employer_ids as well as the discovery coverage function, with regression tests. Local actual-state report correctly gives26configured verified employers, excluding NCBAInsurance/Loop while preserving discovery links. NEXT: commit/deploy this reporting-only fix and reconcile accepted private coverage using an ordinary due-respecting run (do not force refetch or edit state manually). Progress is24active collectors /26verified employer records /12additional against14baseline;28linkedrecords is not28verifiedcompanies. KWFT official home confirms the Conquest career link, but recruitment-host DNS stillfails.

- Final private-state reconciliation COMPLETE: ordinary due-respecting run40294653987 safely refused publication with no due fetch, so no state was promoted by that attempt. Supported explicit healthy single-source refresh40294908186 then succeeded on3938eaa, accepted private183f648. VCB4roles healthy+complete,0newjobs on refresh (1job was already delivered by40293787035). Saved coverage now26verified configured employers,15successfully checked today; NCBAInsurance/Loop both awaiting_employer_verification and not counted. Final312Python tests/lint passed; rebuilt/live HTML acceptance passed32CompanyCareerPage /2782AllJobs, original links, allIDs and metadata/assets. No interactive browser claim (Work browser control disabled at delivery). Progress24active registrycollectors /26verified records /12additional versus14baseline;100target incomplete. All28follow-up checks are recorded in report plus source-checks.csv; remaining27not autoactivated.
- Next expansion priorities: use the now-tested scoped sitemap/JSON-LD collector for other officially linked SnapStar tenant boards (observed spinners and tropicalheatkenya sitemap URLs; employer identity/linkage and full gates still required). Preserve I&M corporate403, Kingdom Incapsula, SMEP/SBM/Umba policy restrictions. M-Oriental FullStack and UBAHeadDigital remain incomplete candidates. Broader ATS/BURN/overnight leads remain available; do not restart credit-limited agents repeatedly. Automation stays ACTIVE with refreshed instructions and quiet notification policy.

### User-requested manual refresh of all feeds — 26 October 2026

- User explicitly requested manual fetches for all feeds. Added a separate `refresh_employers` workflow/CLI flag so healthy approved employer boards are included even when already checked today, without weakening the existing single-source refresh guard. Cooldowns, failure backoff, source verification and API quotas remain enforced. Regression covers multiple healthy boards plus skipped cooldown/backoff and inactive-source rejection.
- Approved selection currently36sources:12base feeds and24registry employer collectors. Dispatch all with batch employer refresh and quota-respecting Google refresh; inspect live workflow before duplicating. Follow through accepted state/live validation and record source failures/skips accurately.

- Manual all-feed run40295869509 on0669936 is RUNNING and has reached Ingest approved sources. Inputs:source=all,refresh_employers=true,refresh_jsearch=true. Selected36approved sources (12base plus24registry employers); cooldowns/backoff and daily/monthly API quotas remain enforced, inactive sources excluded. Hosted code CI40295855128 passed. Published totals remain the previously verified32CompanyCareerPage /2782AllJobs until this run completes; do not claim new totals yet.
- NEXT priority before expansion: monitor existing manual run40295869509 rather than dispatch a duplicate; follow it through accepted private state and live validation, inspect every attempted/skipped/failed source, then save exact totals/results and notify on meaningful completion/failure. The scheduled12EAT run may queue behind it; retain the shared writer and do not edit claims or timestamps.

### Official-portal repairs requested by user — 26 October2026

- Web search confirmed official I&M career-page OpenPositions link to its existing Adrenalin tenant; configured official_careers_url corrected to /ke/career-page/ and official_link evidence recorded. No Adrenalin collector approved yet. Sumac source corrected from unlinked Greenhouse board to official employer /vacancies/; inspected grouped SRO/RO post6957 dated10September2025; no eligibletech or approved full collector. Salaam regulator directory still points to supplied suspended domain; SalaamPay is a banking app, not an alternative careers portal. Prime official indexed page reports0vacancies; robots block retained.
- M-Oriental previously missing fields are now resolved:4scoped inline job cards expose provider IDs6725–6728, independently matched to public WordPress career records. Each explicitly Nairobi,Kenya andFullTime. Functional original post URL for6728 redirects to individual developer job page withHR application email; stable ID is not title-derived. Correct privacy URL /privacy/ reviewed with no automated public-vacancy-metadata restriction identified. Generic inline-card parsing added, no descriptions persisted;314Python tests/lint passed. Local M0 complete4raw/1eligible developer, stillINACTIVE pending hostedM0+trial+publication gates. Evidence docs/employer-discovery/portal-repairs-2026-10-26/. Collected template has no posting/deadline date; use first-found separately (CMS date6October exists only as discovery evidence).
- User manual all-feed run40295869509 SUCCESS, accepted private655cf8a:34successful fetches; GoogleJSearch skippedmonthlyquota andExpertini skippedaccess restriction.9additional jobs (MyJobMag8,Fuzu1); AllJobs2791/CompanyCareerPage32. Scheduled run40296307554 was queued behind it; inspect current runs before new production dispatch.

- M-Oriental hostedM0 40299508802 on0ef3b0d SUCCESS4raw/1technical/1eligible, all checks pass; source verified/inactive pending isolated trial. HostedCI40299385814 and all314Python tests/lint passed. Do not claim developer job live before trial/activation/production. Official I&M/Sumac portal corrections are committed; neither automatically activated.

- M-Oriental isolated trial40299976981 SUCCESS:4raw records/1technical/1eligible/1additional original application URL,3nontechnical excluded. Source activated after review; stable ID6728 and individual WordPress job URL, explicit Nairobi,Kenya. No posting/deadline supplied by collected template; first-found remains separate.314Python tests/lint and hosted CI40299862355 passed. Next targeted production and private/live acceptance. Sumac stale Greenhouse suggestion/pilot rank removed alongside official URL correction; remains inactive.

- Portal repair delivery COMPLETE: M-Oriental production40300532700 onb9fa722 SUCCESS; private625c845,4raw records healthy+complete,1new Nairobi FullStackDeveloper (providerID6728). CompanyCareerPage33 /AllJobs2793 verified by full local-build/live HTML identity/link/order/metadata checks.314Python tests/lint passed; no interactive browser claim. Receipt docs/employer-discovery/portal-repairs-2026-10-26/moriental-production-receipt.json and review.md. User notified of live delivery in commentary; do not repeat unchanged notifications.
- Current progress25active registrycollectors /27verified employerrecords /13additional versus14baseline (29linked records includes2unverifiedNCBA links). Target100stillunfinished. I&M official career URL/link gate repaired but collector/API/policy/trial remain pending. Sumac unlinkedGreenhouse URL corrected to official corporate/vacancies, inactive. Source-checks.csv refreshed;26of latest30bank sources remain inactive. Do not reactivate old pending M-Oriental patches; alreadydelivered.

### User-requested refresh of eight named feed groups — 26 October2026

- Requested:MyJobMag,CorporateStaffing,Other/Google/Linkedin,Fuzu,OpenedCareer,BrighterMonday,Elevolt,TalentSafari. Feed mapping shows Other combines approved jsearch,expertini,camunda,blacksmith,sdg; inactive Careerjet is excluded. TalentSafari is source ashby. Total12approved underlying collectors, without the25registry employer boards.
- Added safe comma-separated workflow source selection (existing CLI already supports repeated --source), with executable workflow-shell regression for multi/single/all/employers selections. Dispatch the named12 with refresh_jsearch=true; quota/access restrictions remain intact. Record actual run ID and status before ending the trigger request.

- Requested eight-feed refresh40301729890 on797c5bf is RUNNING at Ingest approved sources. Exact12source selection:myjobmag,corporate_staffing,jsearch,expertini,camunda,blacksmith,sdg,fuzu,openedcareer,brightermonday,elevolt,ashby. refresh_jsearch=true; registry employer batch refresh is off. HostedCI40301598118 passed; existing Google monthly quota and Expertini access restriction remain enforced. Follow this existing run through accepted state/live checks before any duplicate production dispatch; do not claim refreshed totals yet.

### Pasted recommendation implementation —26October2026

- Corrected advice against repo evidence: KCB Oracle identity is correct; VCB official scoped SnapStar collector is approved; PDF/email formats are not access blocks; Sumac corrected official portal remains authoritative. Automation TOML is ACTIVE; earlier agent credit exhaustion does not mean paused. No duplicate automation or automatic source approvals.
- Implemented silent discovery baselines and private employer-review-queue.json for newly observed vacancy/PDF links or technical title metadata. Failures/partial/blocks keep old baseline, corrected URLs reset quietly, tracking noise ignored, no descriptions/public jobs/closures/collector counts from monitoring. Existing budgets/robots/throttles unchanged.318Python tests/lint passed locally. Queue first appears when new code runs; before changing production inspect current manual feed run40301729890 and avoid duplicate full refresh.
- HFC/Equity public HTML and linked JS assets checked: loading/default-empty states are unconfirmed inventory. Indexed HFCSystemAdministrator338 not approved as current; Equitylive data/pagination unverified. Source review reasons updated, not activated. Evidence docs/employer-discovery/recommendation-review-2026-10-26/.

### Completed refresh and monitoring deployment —26October2026

- Requested eight-feed refresh40301729890 completed SUCCESS, accepted private af9a14c:10sources successful, GoogleJSearch monthly-quota skip and Expertini access-restriction skip.4additional jobs (MyJobMag2, CorporateStaffing2). No restriction bypass.
- Monitoring deployment40304226748 on e5987a2 completed SUCCESS, accepted private4cc4c9b. Targeted healthy M-Oriental refresh returned4complete raw records,0newjobs; public output unchanged. Private employer-review-queue.json exists with0pending signals; a quiet baseline/empty queue is not employer coverage or new jobs.318Python tests/lint and hosted CI40303994324 passed.
- Rebuilt accepted public data locally and verified deployed HTML:2797AllJobs /33CompanyCareerPage, feed second afterAll, all accepted identities/original links and canonical/assets/robots/sitemap pass. Interactive browser remains unavailable; no interactive acceptance claim. Receipt docs/employer-discovery/recommendation-review-2026-10-26/production-receipt.json.
- Expansion unchanged25active registrycollectors /27verified employerrecords /13additional versus14baseline;100additional target unfinished. Next work should prioritize actual technical vacancies on reusable ATS/scoped SnapStar platforms, with official linkage, policy/access, complete extraction, hosted/trial/publication gates. Keep loading shells unconfirmed and credit-limited agents stopped.

### BURN vacancy-first investigation —26October2026

- Complete local JazzHR M0 for BURN employer_8aa05ad779651797:22raw records,1eligible Nairobi InformationSecurityLead Qc0FDbVNVK. Official careers page observed script links exact board; discovery literal-link extraction corrected without executing JavaScript, with regression. CarbonProjectManager false positive excluded narrowly; existing generic product/project policy preserved.319Python tests/lint passed.
- BURN remains PENDING: corporate-linked privacy URL returns a soft404 despite HTTP200, so collection_review=false; no hosted/trial/publication approval inferred. Hosted discovery can verify extraction/access but cannot clear missing policy. Evidence docs/employer-discovery/burn-review-2026-10-26/. Do not count this candidate as company coverage or a published job.
- TropicalHeat/Spinners official careers pages do not establish observed SnapStar tenant linkage. Indexed TropicalHeat HeadTechnology deadline16October is expired; don't publish. No duplicate writer dispatched; prior production40304226748 remains latest completed run. Target100stillunfinished (13additional verified).

- BURN hosted M0 40316620890 on07f03dc SUCCESS:22raw/2title-classified/1eligible (InformationSecurityLead Kenya Qc0FDbVNVK); every extraction/linkage check true, hosted CI40316600046 SUCCESS. Runner-access evidence saved. Collection-policy gate remains false because linked privacy is soft404: NO trial, activation or production dispatch for BURN. Progress unchanged13additional verified. Next vacancy-first leads saved: SALIXDataAfrica SmartRecruiters Nairobi MidLevelDeveloper744000146204970 and AmaliTech board; verify official linkage/current board/policy/explicit role locations before collectors. Incentro company-level Kenya references are not vacancy eligibility.

### Pending ATS batch review —26October2026

- Fresh complete local checks: NALA2technical jobs bothLondonUK,0eligible; Genesis2roles,0technical; olddLocalLever40raw/6technical/0eligible; AZAAPI404 (notempty). Evidence docs/employer-discovery/pending-platform-batch-2026-10-26/.
- NALA official Workable link confirmed, but observed AUP scraping/copying restrictions on its Service need external-ATS scope review; manual pendingreview. AZA terms explicitly prohibit robot/automatic monitoring and copying; manual, no further automated retries/bypass. Genesis officiallink/policy unconfirmed.
- dLocal official /careers redirects to Nodi /company/dlocal. Discovery URL corrected to observed official portal; historical Lever retained import reference, no current linkage assumed. Nodi dynamic shell has no JobPosting/scoped links: notzero inventory and not a functioning collector.
- SALIX official homepage does not establish SmartRecruiters linkage; AmaliTech old careers URLs redirect to host whose robots returned405. Stopped without bypass. Both uncounted. No sources activated; verified progress remains25collectors/27companies/13additional.
- Scheduled production40319281030 was already in progress when this heartbeat began; no duplicate production dispatched. Inspect/follow its accepted private state and live validation before another writer. Current review-queue snapshot before that run had0pending entries.

- Scheduled40319281030 SUCCESS, accepted private dc91674:15new jobs (MyJobMag8,CorporateStaffing4,Elevolt2,OpenedCareer1). Local rebuild/live HTML checks passed2812AllJobs /33CompanyCareerPage, allacceptedIDs/original links/secondfeedorder/metadata/assets. No interactive browser claim. Private reviewqueue0pending; new successful watch baselines nonetheless expose leads, not job approvals. Reviewing CrossBoundary SystemsSecurityEngineer and TechnoBrain explicitKenya roles; LTWP ITIntern deadline24June is expired and excluded. Registry count unchanged13additional.

### CrossBoundary candidate from fresh watch baseline —26October2026

- Official employer page embeds18links to exact JazzHR tenant. Local complete M0:18raw/1technical/1eligible SystemsSecurityEngineer K2r7WGkQmC. Privacy/robots and vacancy metadata scope reviewed; no automation restriction identified, no express licence claimed. Pending hosted M0/trial/publication; NOT yet active.
- Provider default Mumbai omits vacancy's explicit candidate office alternatives. New opt-in description_location_pattern extracts only that job-scoped location paragraph in RAM; generic company-office boilerplate does not qualify (regression). Lists African offices subject to local work authorisation; normalizedSouthAfrica is one valid offered office, not invented Kenya-only/remote eligibility.321Python tests/lint passed. Source remains absence-off and employers distinct.

- CrossBoundary hostedM0 40324526722 on4d2a3ab SUCCESS18raw/1technical/1eligible, allchecks pass; CI40324490629 SUCCESS. Status verified/inactive. NEXT isolated hosted trial then publication review before activation/production; no new livecompany yet.

- CrossBoundary isolated trial40324776037 on6dca99d SUCCESS18raw/1technical/1eligible/1additionalunique;17nontechnical withheld, accepted baseline supplied. Publication review approved activation after allgates. NEXT production/private/live validation; not yet claimedlive. TechnoBrain next lead:11current cards,4explicitKenya tech candidates with providerIDs7419,7408,4838,7416 confirmed from detailshortlinks. Requires scoped listing-location joining with detailIDs, own-body technical context and policy review; no trial/activation yet.

- Activation validation caught an existing shared tenant: employer_4b5f0d16f35b56cb already collects CrossBoundary for Energy. No production dispatched with the duplicate. Corrected: retain original active sourceID, retire duplicate-fetch candidate18db, keep Group and Energy as distinct employerIDs. Group linked but NOT added to verified_employer_ids yet. Scoped location fix transferred to existing tenant (already passed candidate local/hosted/trial); repeat hosted M0/trial on preserved sourceID before targeted production. Activecollector count remains25, not26. Earlier activation wording is superseded.

- Shared CrossBoundary source hostedM0 40325324474 SUCCESS18raw/1eligible; preserved-ID isolated trial40326303820 SUCCESS1additionalunique. Group added to verified_employer_ids after individual role/link evidence; Energy retained distinct.25active collectors (no duplicate-fetch count), pending production publication/coverage reconciliation before reporting28verified/14additional. SourceID4b5f retained; candidate18db retired before any production. NEXT targeted healthy refresh after current code checks.
- TechnoBrain generic scoped-card metadata fallback implemented/tested: details supply immutable WordPress IDs, exact-card titles/locations supply job-scope geography; unmatched cards/title conflicts fail completeness, no footer geography. Original external ApplyNow destinations preserved.324Python tests/lint passed; real local M0 11raw/5tech/3eligible after exact URL/title/location joins.2eligible roles have original Zoho destinations; AutomationEngineer CTA lacks destination and stays unresolved. Source PENDING, official root-link/hosted/trial/application gates unfinished. Evidence docs/employer-discovery/technobrain-review-2026-10-26/. No TechnoBrain job live.

- Current hosted CI40326670635 on67d0851 SUCCESS (324Python tests plus frontend checks). Targeted CrossBoundary production40326952809 dispatched on67d0851 with source=employer_4b5f0d16f35b56cb,refresh_employer=true after checks. Follow THIS run through accepted private state/live validation before dispatching any duplicate writer. Candidate18db is retired; original4b5source retains IDs. Pending live coverage reconciliation should be25collectors/28verified employers/14additional if production succeeds; do not claim those delivery totals yet. TechnoBrain remains pending with application and official-link gates false; read-only hosted discovery dispatched separately, never a production approval.
- TechnoBrain hosted discovery40327010870 on67d0851 is read-only/in progress; application URL syntax checks alone cannot clear the source's explicit application_links=false gate for its unconfirmed AutomationEngineer CTA. No TechnoBrain trial or activation approved. Inspect its artifact before further hosted checks.

- TechnoBrain hostedM0 40327010870 SUCCESS11raw/5technical/3eligible, matching local stableIDs and scopedKenya fields. Runner_access recorded; manual application_links=false and official_link=false gates retained rather than copied from syntactic discovery checks. Stillinactive, no trial.2originalZoho applications verified; inspect missingAutomationEngineer CTA/linkedZoho board next.

- CrossBoundary production40326952809 on67d0851 SUCCESS, accepted private79d7945:18healthy complete raw records,1new SystemsSecurityEngineer published under original4b5sourceID. Local-build/live HTML checks pass34CompanyCareerPage /2813AllJobs. Source remains absence-off. Final coverage check caught a missing reciprocal Group employer.source_ids backlink: private dailycoverage still27 although active sources verify28. Correct backlink in config/employers.yaml, with graph-integrity regression; reconcile accepted coverage through supported healthy targeted refresh before final14additional claim. No manual private-state edits or claim deletion.
