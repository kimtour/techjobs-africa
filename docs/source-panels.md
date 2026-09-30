# Independent source panels

## Scope and reference

Requested 2026-09-30: reproduce the independent source feeds at
https://techurls.com/, including load-more and Latest • Day • Week • Month.
Browser inspection found 15 initially rendered stories per source and a 334px
scrolling body at the inspected viewport. The source header is outside that body.
Clicks on Load more and Day did not produce a changed selection/result in that
session, so the reference's server-side filtering/ranking is unverified.

## Implementation contract

- Keep the existing two-column layout and source colors, collapsing to one column
  on narrow screens. Each body is 26rem high (24rem on mobile), independent of
  result count. Headers and status lines are outside the scrolling body.
- Initially expose 10 jobs per source, with Load more jobs exposing 10 more from
  the static export. No runtime fetch or backend is required.
- Loading more retains the feed's scroll position and leaves all other sources'
  period, pagination, scroll position, and layout unchanged.
- Latest sorts dated active jobs newest first, then undated jobs, with stable ID
  tie-breaking. Restricted jobs remain excluded.
- Day, Week, Month select publication dates from the past 24 hours, 7 days, and
  30 days, inclusive. Date-only values use UTC midnight, consistent with their
  display. Undated, invalid, and future dates do not match a bounded period.
- A source period resets only that source to 10 rows and scrolls its body to top.
- Search and category apply across sources and reset pagination/scroll; periods
  remain selected. Empty feeds retain titles, controls, and a recovery message.
- Scroll regions support keyboard focus, visible focus, and contained overscroll.
  Buttons expose selection using aria-pressed; counts use a polite status region.

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
