# Claude Code project guidance

Read and follow @AGENTS.md for shared repository commands, architecture, and safety constraints.
Read @PROJECT_CONTEXT.md before architectural changes. Inspect the current code and
`docs/source-discovery.md` before deciding which development phase is complete;
do not restart M0 just because the original specification lists it first.

## Frontend changes

- This frontend currently uses Astro, TypeScript, and plain CSS, not Tailwind.
- Follow `docs/source-panels.md` for source feed behavior and verification.
- Keep source headings outside the fixed-height scroll region. Loading jobs or
  changing one source's period must not move other sources or reset their state.
- Empty periods retain their source header, controls, and a recovery message.
- Latest includes undated active jobs; Day/Week/Month use source publication
  dates over the last 24 hours/7 days/30 days. Never substitute crawl timestamps.
- Preserve escaped rendering and approved outbound application URLs.

## Delivery workflow

1. Inspect existing changes and preserve unrelated user work.
2. Record the scope and acceptance criteria before implementation.
3. Run `npm test --prefix site`, `npm run check --prefix site`, and
   `npm run build --prefix site`; run Python tests and lint for ingestion changes.
4. Verify scrolling, load-more, periods, empty states, search, and mobile layout
   in a real browser. A passing build alone does not verify interactions.
5. Deploy when requested using the existing GitHub Actions/Cloudflare workflow.
   Credentials stay in GitHub Secrets. Confirm the deployment step actually ran.
6. Verify the deployed URL and report the commit, test evidence, and any blockers.
   Never describe an unverified deployment or unfinished phase as complete.
