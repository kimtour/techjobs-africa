# Independent source panels

## Scope and reference

Requested 2026-09-30: reproduce the independent source feeds at
https://techurls.com/, including load-more and source period controls.
Browser inspection found 15 initially rendered stories per source and a 334px
scrolling body at the inspected viewport. The source header is outside that body.
Clicks on Load more and Day did not produce a changed selection/result in that
session, so the reference's server-side filtering/ranking is unverified.

## Ingestion guardrail

Source category pages are not a substitute for title-level technical evidence.
They can include unrelated listings; the pipeline rejects every job that cannot
be deterministically classified from its own title or narrowly validated technical evidence in its own listing, including HR and finance
roles found on BrighterMonday's Engineering & Technology and Software & Data pages.

## Implementation contract

- Employer onboarding keeps the employer registry as an internal collection
  inventory. Only actual vacancies enter All Jobs; careers websites are not job
  cards. The Company Career Page feed shows accepted direct-employer vacancies
  immediately after All Jobs, including future registry vacancies only after
  production activation and validation. Trials and discovery links never populate
  it. It retains its header and controls when empty.
  Direct-employer, employer and sector controls are global filters: like search
  and category, they reset pagination/scroll while retaining each panel's period.
  Employer and sector controls appear only when accepted job metadata supplies
  them. Registry entries never count as jobs. Existing source order is retained.

- Feed order updated on 25 October 2026: All Jobs, Company Career Page, MyJobMag,
  Corporate Staffing, Other/Google/Linkedin, Fuzu, OpenedCareer, BrighterMonday, Elevolt, TalentSafari.
  Desktop reads left to right across the two columns; mobile uses this sequence
  in one column. All Jobs contains each active, unrestricted job once, newest first,
  and displays its source. It shares the independent period and pagination controls.
  Global result counts count unique jobs across matching feeds.
- Other/Google/Linkedin is fifth, after Corporate Staffing and before Fuzu.
  It combines Kenya and Africa/worldwide remote Google Jobs discoveries, previously accepted LinkedIn jobs,
  direct Expertini sitemap listings, verified public Camunda/Blacksmith/SDG remote career postings,
  and Careerjet if that provider is activated. Each job retains its true publisher
  label and original application destination. Jobs also appear in All Jobs;
  source feeds include every job attributed to that source even when cross-listed.
  Mobile keeps the same feed sequence. An empty LinkedIn feed retains its controls.
- Keep source colors, collapsing to one column
  on narrow screens. Each body is 26rem high (24rem on mobile), independent of
  result count. Headers and status lines are outside the scrolling body.
- Latest initially exposes 10 jobs per source, with Load more jobs exposing 10
  more from the static export. Day, 3 Days, Week, 2 Weeks, and Month expose
  every matching job in that source's scroll region. No runtime fetch or backend
  is required.
- Loading more retains the feed's scroll position and leaves all other sources'
  period, pagination, scroll position, and layout unchanged.
- Latest sorts by employer posting date, falling back to labelled First found
  dates where available, then undated jobs, with stable ID
  tie-breaking. Restricted jobs remain excluded.
- Day, 3 Days, Week, 2 Weeks, and Month select employer posting dates (or labelled First found fallback) from the past
  24 hours, 3 days, 7 days, 14 days, and 30 days, inclusive. Date-only values
  use UTC midnight, consistent with their display. Undated, invalid, and future
  dates do not match a bounded period.
- A source period resets only that source and scrolls its body to top. Latest
  returns to 10 rows; every bounded period exposes every matching row.
- Search and category apply across sources and reset pagination/scroll; bounded
  periods remain fully expanded. Empty feeds retain titles, controls, and a
  recovery message.
- Scroll regions support keyboard focus, visible focus, and contained overscroll.
  Buttons expose selection using aria-pressed; counts use a polite status region.
- Opened job titles turn purple immediately in both All Jobs and their source
  feed. Stable job IDs are remembered in browser storage across reloads; when
  storage is unavailable, the colour still updates for the current page.
  Open tabs sync opened jobs on storage updates, focus, and history restoration.
  The interaction script uses a build-generated versioned URL to refresh with
  each release; the original script URL remains available for older pages.

## Delivery plan and acceptance

1. Inspect reference and current site; identify expanding feeds and disappearing
   empty sources as regressions to address.
2. Implement contained bodies, independent updates, sorting, and empty states.
3. Run frontend behavior tests, Astro check/build, and existing Python tests/lint.
4. Browser-check real data: scroll/load one source and compare header/neighbor
   positions; change periods and recover from empty; search/category; narrow layout.
5. Deploy the tested commit through the existing GitHub Actions workflow and verify
   the actual Cloudflare deployment and live interaction behavior.

Automated regression tests: `npm test --prefix site` (also in deployment CI).
Build checks: `npm run check --prefix site && npm run build --prefix site`.

## Rollback

Revert the source-panel commit and rerun the existing deployment workflow, or
restore the previous successful deployment through Cloudflare Pages. Do not
rewrite the persistent data branch to roll back a frontend change.


Expertini's RSS supplies original titles and RSS publication dates; these records
participate in date periods and carry Expertini RSS labels. Sitemap-only records
have labelled URL-derived technical titles and unknown dates, so they appear in
Latest and All Jobs and are absent from bounded periods. No separate Expertini
panel is added. Same-ID source refreshes preserve cross-source attribution.

## Company Career Page delivery — 25 October 2026

Revision `9f79691` deployed successfully through run
[40200704093](https://github.com/kimtour/techjobs-africa/actions/runs/40200704093).
Local and live browser checks confirmed second-feed placement on desktop and
390px mobile, fixed-height bodies with external headers, load-more scroll/layout
isolation, empty-period recovery and direct filtering. HTML verification matched
all 14 company vacancies and all 2,760 accepted All Jobs identities. Shared cards
do not inflate global counts. New registry sources remain gated and inactive.
The final code passed 255 Python tests, 14 frontend tests and hosted scheduler
checks in validation run 40198930006.
