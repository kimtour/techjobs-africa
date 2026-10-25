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
